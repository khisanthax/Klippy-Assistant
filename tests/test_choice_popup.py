import pytest
from PySide6.QtWidgets import QApplication

from klippy.clarification import popup_position
from klippy.conversation import Conversation
from klippy.domain import Parameter, Printer
from klippy.macros import discover
from klippy.orb_geometry import Rect
from klippy.safety import NeedsParameter, Rejected


def macros(rig, parameter=False):
    store, sim, engine, _ = rig
    sim.config = {
        "gcode_macro BED_MESH_FAST": {"gcode": "G28\nG1 X10"},
        "gcode_macro BED_MESH_FULL": {"gcode": "G28\nG1 X20"},
    }
    if parameter:
        sim.config = {"gcode_macro LOAD_FILAMENT": {"gcode": "G1 E{params.LENGTH}"}}
    registry, _ = discover(sim.config, {})
    registry = {
        k: m.model_copy(
            update={
                "approved": True,
                "reviewed": True,
                "enabled": True,
                "parameters": {"LENGTH": Parameter(minimum=1.0, maximum=10.0)} if parameter else {},
            }
        )
        for k, m in registry.items()
    }
    store.replace_macros("sim", registry)
    return Conversation(engine, clock=lambda: rig[3][0])


@pytest.mark.parametrize("selection", ["first one", "second one", "BED_MESH_FAST",'bed mesh fast'])
async def test_actual_approved_ambiguity_selection_only_proposes(selection, rig):
    c = macros(rig)
    with pytest.raises(Rejected, match="Which macro"):
        await c.hear("run a bed mesh")
    assert len(c.choice.names) == 2 and not rig[1].writes
    response = await c.hear(selection)
    assert "Confirm" in response and rig[2].pending and not rig[1].writes


async def test_one_clear_macro_has_no_popup(rig):
    c = macros(rig)
    assert "Confirm" in await c.hear("BED_MESH_FAST")
    assert c.choice is None and not rig[1].writes


async def test_remembered_choice_never_authorizes_and_changed_definitions_invalidate(rig):
    c = macros(rig)
    store, sim, engine, _ = rig
    with pytest.raises(Rejected):
        await c.hear("bed mesh")
    c.choice.remember = True
    await c.hear("first one")
    assert store.get("remembered_choices") and not sim.writes
    engine.cancel()
    assert "Confirm" in await c.hear("bed mesh") and not sim.writes
    engine.cancel()
    sim.config["gcode_macro BED_MESH_FAST"]["gcode"] = "G1 X80"
    with pytest.raises(Rejected):
        await c.hear("bed mesh")
    assert store.get("remembered_choices") == {} and not sim.writes


@pytest.mark.parametrize(
    "change", ["definition", "removed", "rename", "printer", "expired", "cancel", "unrelated"]
)
async def test_stale_choices_cannot_authorize(change, rig):
    c = macros(rig)
    store, sim, engine, clock = rig
    with pytest.raises(Rejected):
        await c.hear("bed mesh")
    if change == "definition":
        sim.config["gcode_macro BED_MESH_FAST"]["gcode"] = "G1 X99"
    elif change == "removed":
        sim.config.pop("gcode_macro BED_MESH_FAST")
    elif change == "rename":
        sim.config["gcode_macro BED_MESH_NEW"] = sim.config.pop("gcode_macro BED_MESH_FAST")
    elif change == "printer":
        store.save_printer(Printer(id="other", name="Other", url="http://127.0.0.1:1", approved=True))
        engine.select("other")
    elif change == "expired":
        clock[0] += 31
    elif change == "cancel":
        await c.hear("cancel that request")
    else:
        await c.hear("status")
    with pytest.raises(Rejected):
        await c.hear("first one")
    assert not sim.writes and engine.pending is None


async def test_missing_values_popup_validates_bounds_and_requires_confirmation(rig):
    c = macros(rig, parameter=True)
    with pytest.raises(NeedsParameter):
        await c.hear("load filament")
    assert c.choice.parameter is not None
    with pytest.raises(Rejected):
        await c.hear("LENGTH=100")
    assert not rig[1].writes
    with pytest.raises(NeedsParameter):
        await c.hear("load filament")
    assert "LENGTH=5" in await c.hear("LENGTH=5") and not rig[1].writes


@pytest.mark.parametrize(
    "work,orb",
    [
        (Rect(0, 0, 1920, 1040), Rect(1700, 830, 192, 192)),
        (Rect(-1920, 0, 1920, 1000), Rect(-1920, 0, 128, 128)),
        (Rect(0, 40, 600, 400), Rect(450, 250, 128, 128)),
    ],
)
def test_popup_placement_stays_in_usable_area(work, orb):
    x, y, w, h = popup_position(orb, work, 400, 340)
    assert work.x <= x <= work.x + work.width - w and work.y <= y <= work.y + work.height - h


async def test_mouse_selection_resolves_through_normal_confirmation(rig):
    from klippy.app import Window

    app = QApplication.instance() or QApplication([])
    macros(rig)
    window = Window(rig[0], smoke=True)
    window.timer.stop()
    window.engine.clients = rig[2].clients
    c = window.conversation
    try:
        with pytest.raises(Rejected):
            await c.hear("bed mesh")
        popup = window.clarification_popup
        popup.refresh()
        assert popup.isVisible() and not popup.remember.isChecked()
        popup.radios[0][1].setChecked(True)
        jobs = []
        window.worker.submit = lambda name, job: jobs.append(job)
        popup.continue_choice()
        result = await jobs.pop()
        window.result("turn", result)
        assert window.engine.pending is not None and not rig[1].writes
    finally:
        window.quit()
        window.deleteLater()
        app.processEvents()
