import pytest

from app.models import Storyboard
from app.render import ApprovalRequired, create_render_request


def test_render_requires_explicit_approval() -> None:
    storyboard = Storyboard(title="Weekend", caption="A bright trip.")

    with pytest.raises(ApprovalRequired):
        create_render_request(storyboard, approved=False)
