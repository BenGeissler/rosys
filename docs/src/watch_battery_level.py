#!/usr/bin/env python3
from nicegui import ui
import rosys
import rosys.ui
from rosys.actors import Actor
from rosys.automations import drive_path
from rosys.world import Mode, PathSegment, Pose, Spline, World

runtime = rosys.Runtime(world=World(mode=Mode.SIMULATION))
rosys.ui.configure(ui, runtime)


class BatteryGuard(Actor):

    def __init__(self) -> None:
        super().__init__()
        rosys.event.register(rosys.event.Id.NEW_MACHINE_DATA, self.check_battery)

    async def check_battery(self):
        if self.world.robot.battery < 24:
            await rosys.event.call(rosys.event.Id.PAUSE_AUTOMATIONS, 'battery level is below 24 V')


runtime.with_actors(BatteryGuard())
voltage = ui.label()
ui.timer(1, lambda: voltage.set_text(f'{runtime.world.robot.battery:.1f} V, pose: {runtime.world.robot.prediction}'))
path = [PathSegment(spline=Spline.from_poses(Pose(), Pose(x=10, y=2)))]
runtime.automator.default_automation = lambda: drive_path(runtime.world, runtime.hardware, path)
rosys.ui.automation_controls()

ui.run(title='RoSys', port=8080)