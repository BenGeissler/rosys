from enum import Enum
from rosys.actors.esp import Esp
from rosys.actors.actor import Actor
from rosys.world.world import World, WorldState


class State(Enum):
    IDLE = 1
    INITIALIZING = 2
    STEERING = 3
    STOPPING = 4


class Steerer(Actor):
    interval: float = 0.05

    def __init__(self, esp: Esp):
        super().__init__()
        self.esp = esp
        self.world_state = None
        self.state = State.IDLE
        self.orientation = None
        self.linear_speed = 0
        self.angular_speed = 0

    def start(self):
        self.log.info('start steering')
        self.state = State.INITIALIZING
        if self.world.state == WorldState.RUNNING:
            self.log.info('pausing automations')
            self.world_state = self.world.state
            self.world.state = WorldState.PAUSED

    def update(self, x: float, y: float):
        if self.state == State.INITIALIZING:
            squared_distance = x**2 + y**2
            dead_zone = 0.1
            if squared_distance > dead_zone**2:
                is_down = y < 0 and abs(y) > abs(x)
                self.orientation = -1 if is_down else 1
                self.state = State.STEERING

        if self.state == State.STEERING:
            self.linear_speed = y
            self.angular_speed = -x * self.orientation

    def stop(self):
        self.log.info('stop steering')
        self.orientation = None
        self.state = State.STOPPING

    async def step(self):
        if self.state == State.STEERING:
            await self.esp.drive(self.linear_speed, self.angular_speed)
        elif self.state == State.STOPPING:
            await self.esp.drive(0, 0)
            if self.world_state is not None:
                self.world.state = self.world_state
                self.world_state = None
            self.state = State.IDLE

    def __str__(self) -> str:
        return f'{type(self).__name__} ({self.state})'
