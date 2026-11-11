from unittest.mock import patch

import httpx
import pytest

from klippy.conversation import LocalLLM
from klippy.safety import Rejected


async def interpret(content, text):
    response = httpx.Response(200, json={"choices": [{"message": {"content": content}}]},
                              request=httpx.Request("POST", "http://127.0.0.1"))
    async def post(*args, **kwargs):
        return response
    with patch("httpx.AsyncClient.post", post):
        return await LocalLLM().interpret(text, "sim", {})


async def test_schema_valid_hallucinated_action_rejected():
    content = '{"intent":{"action":"home","printer_id":"sim","params":{}},"question":null}'
    with pytest.raises(Rejected, match="explicitly"):
        await interpret(content, "do the thing")


async def test_clarification_envelope_never_becomes_action():
    with pytest.raises(Rejected, match="clarify"):
        await interpret('{"intent":null,"question":"Which operation?"}', "do the thing")


async def test_conflicting_envelope_never_executes():
    with pytest.raises(Rejected):
        await interpret('{"intent":{"action":"home","printer_id":"sim"},"question":"Are you sure?"}', "home")


async def test_correct_action_evidence_retains_intent():
    result = await interpret('{"intent":{"action":"pause","printer_id":"sim"},"question":null}',
                             "Could you pause it please?")
    assert result.action.value == "pause"


async def test_other_printer_output_rejected():
    with pytest.raises(Rejected, match="another printer"):
        await interpret('{"intent":{"action":"pause","printer_id":"other"},"question":null}', "pause")
