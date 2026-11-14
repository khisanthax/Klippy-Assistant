from types import SimpleNamespace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from klippy.app import Window
from klippy.voice import VoiceLoop


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
        def click():
            window.sprite.mousePressEvent(SimpleNamespace(button=lambda:Qt.MouseButton.LeftButton,
                                                           globalPosition=lambda:QPointF(5,5)))
            window.sprite.mouseReleaseEvent(object())
        click()
        assert not voice.enabled.is_set() and voice.listen_until==0
        assert window.engine.pending is None and not rig[1].writes
        click()
        assert voice.enabled.is_set() and voice.listen_until==0
    finally:
        window.quit()
        window.deleteLater()
        app.processEvents()
