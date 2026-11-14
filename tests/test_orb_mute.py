from types import SimpleNamespace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from klippy.app import Window
from klippy.voice import VoiceLoop


async def test_request_exception_keeps_turn_identity_and_cannot_speak_after_mute(rig, monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = Window(rig[0], smoke=True)
    window.timer.stop()
    voice = VoiceLoop(SimpleNamespace(reset_wake=lambda:None),lambda _:None,lambda _:None,
                      session=window.conversation.session)
    window.voice = voice
    voice.enabled.set()
    rig[0].set('listening', {'mode':'always'})
    jobs=[]
    monkeypatch.setattr(window.worker,'submit',lambda name,coroutine:jobs.append(coroutine))
    async def broken(*args,**kwargs):
        raise RuntimeError('Synthetic internal fault; must not be spoken')
    monkeypatch.setattr(window.conversation,'hear',broken)
    try:
        window.submit_turn('status')
        result=await jobs.pop()
        assert result[2] is True and 'Synthetic internal' not in result[1]
        window.toggle_listening()
        window.result('turn', result)
        assert voice.speech.empty() and not window.command_busy
        assert 'Operation failed' not in window.output.toPlainText()
    finally:
        window.quit()
        window.deleteLater()
        app.processEvents()


def test_single_orb_click_mutes_immediately_and_unmute_requires_new_wake(rig):
    app = QApplication.instance() or QApplication([])
    window = Window(rig[0], smoke=True)
    window.timer.stop()
    voice = VoiceLoop(SimpleNamespace(reset_wake=lambda: None), lambda _:None, lambda _:None,
                      session=window.conversation.session)
    window.voice = voice
    rig[0].set('listening', {'mode':'always'})
    voice.enabled.set()
    voice.session.touch()
    try:
        window.command_busy = True
        old_turn = window.turn
        window.sprite.pipeline_event('Thinking')
        def click():
            window.sprite.mousePressEvent(SimpleNamespace(button=lambda:Qt.MouseButton.LeftButton,
                                                           globalPosition=lambda:QPointF(5,5)))
            window.sprite.mouseReleaseEvent(object())
        click()
        assert not voice.enabled.is_set() and voice.listen_until==0
        assert window.engine.pending is None and not rig[1].writes
        assert not window.command_busy and window.send_button.isEnabled()
        window.result('turn', (old_turn, 'Stale response must not play', False))
        assert voice.speech.empty() and window.sprite.state == 'muted'
        click()
        assert voice.enabled.is_set() and voice.listen_until==0
    finally:
        window.quit()
        window.deleteLater()
        app.processEvents()
