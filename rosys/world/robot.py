from pydantic import BaseModel
from .pose import Pose
from .velocity import Velocity


class Robot(BaseModel):

    pose: Pose = Pose()
    velocity: Velocity = Velocity()
    battery: float = 0
    temperature: float = 0