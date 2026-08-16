from dataclasses import dataclass

from app.models import Storyboard


class ApprovalRequired(Exception):
    """Raised when a render is requested before the user approves its plan."""


@dataclass(frozen=True)
class RenderRequest:
    title: str
    caption: str
    output_format: str = "vertical-mp4"


def create_render_request(storyboard: Storyboard, approved: bool) -> RenderRequest:
    if not approved:
        raise ApprovalRequired("Approve the plan before creating a video.")

    return RenderRequest(title=storyboard.title, caption=storyboard.caption)
