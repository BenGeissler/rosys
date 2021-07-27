import sys
import asyncio
import logging
from typing import Awaitable, Callable, Union, get_type_hints
from . import task_logger
from .persistence import backup, restore
from .actors.actor import Actor
from .actors.detector import Detector
from .actors.detector_simulator import DetectorSimulator
from .actors.esp import SerialEsp, MockedEsp
from .actors.odometer import Odometer
from .actors.steerer import Steerer
from .actors.robot_locator import RobotLocator
from .actors.automator import Automator
from .actors.camera_scanner import CameraScanner
from .actors.camera_downloader import CameraDownloader
from .actors.camera_linker import CameraLinker
from .actors.camera_simulator import CameraSimulator
from .actors.camera_projector import CameraProjector
from .world.world import World, WorldState
from .world.mode import Mode
from .helpers import print_stacktrace


class Runtime:

    def __init__(self, world: World, additional_actors: list[Actor] = []):

        self.world = world

        restore(self.world)

        self.esp = SerialEsp() if world.mode == Mode.REAL else MockedEsp(self.world)
        self.odometer = Odometer()
        self.steerer = Steerer()
        self.robot_locator = RobotLocator()
        self.automator = Automator()
        self.detector = Detector() if world.mode == Mode.REAL else DetectorSimulator()
        self.camera_projector = CameraProjector()
        self.camera_linker = CameraLinker()

        if world.mode == Mode.REAL:
            camera_actors = [CameraScanner(), CameraDownloader()]
        else:
            camera_actors = [CameraSimulator()]

        self.actors = [
            self.esp,
            self.odometer,
            self.steerer,
            self.robot_locator,
            self.automator,
            *camera_actors,
            self.camera_projector,
            self.camera_linker,
            self.detector,
        ] + additional_actors

        self.follow_ups = {
            self.esp.step: [
                self.odometer.handle_velocity,
            ],
            self.detector.step: [
                self.robot_locator.find_robot,
                self.odometer.handle_detection,
            ],
        }

    async def pause(self):
        self.world.state = WorldState.PAUSED
        await self.esp.drive(0, 0)

    def resume(self):
        self.world.state = WorldState.RUNNING

    async def run(self, seconds: float = sys.maxsize):

        self.tasks = []
        end_time = self.world.time + seconds

        if self.world.mode == Mode.TEST:
            self.tasks.append(task_logger.create_task(self.advance_time(end_time)))

        for actor in self.actors:
            if actor.interval is not None:
                self.tasks.append(task_logger.create_task(self.repeat(actor, end_time)))

        await asyncio.gather(*self.tasks)

    async def stop(self):

        backup(self.world)
        [t.cancel() for t in self.tasks]
        [await a.tear_down() for a in self.actors]

    async def call_follow_ups(self, trigger: Union[Callable, Awaitable]):

        for follow_up in self.follow_ups.get(trigger, []):
            params = self.get_params(follow_up)
            await follow_up(*params) if asyncio.iscoroutine(follow_up) else follow_up(*params)
            await self.call_follow_ups(follow_up)

    async def repeat(self, actor: Actor, run_end_time: float):

        params = self.get_params(actor.step)

        while self.world.time < run_end_time:

            start = self.world.time
            try:
                await actor.step(*params)
                await self.call_follow_ups(actor.step)
                dt = self.world.time - start
            except:
                dt = self.world.time - start
                print_stacktrace()
                if actor.interval == 0 and dt < 0.1:
                    delay = 0.1 - dt
                    logging.warning(
                        f'{type(actor).__name__} would be called to frequently ' +
                        f'because it only took {dt*1000:.0f} ms; ' +
                        f'delaying this step for {delay*1000:.0f} ms')
                    await asyncio.sleep(delay)

            if dt > actor.interval > 0:
                logging.warning(f'{type(actor).__name__} took {dt} s')

            if self.world.mode == Mode.TEST:
                sleep_end_time = self.world.time + actor.interval
                while self.world.time <= min(run_end_time, sleep_end_time):
                    await asyncio.sleep(0)
            else:
                await asyncio.sleep(actor.interval - dt)

    async def advance_time(self, end_time):

        while self.world.time <= end_time:
            self.world.set_time(self.world.time + 0.01)
            await asyncio.sleep(0)

    def get_params(self, func: Union[Callable, Awaitable]):

        params = []
        for name, type_ in get_type_hints(func).items():
            for obj in [self.world] + self.actors:
                if isinstance(obj, type_):
                    params.append(obj)
                    break
            else:
                raise Exception(f'parameter "{name}" of type {type_} is unknown')

        return params
