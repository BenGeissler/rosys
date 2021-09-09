from nicegui.elements.scene_objects import Extrusion, Group, Sphere
from nicegui.elements.scene_object3d import Object3D
from rosys.world.robot import Robot


class RobotObject(Object3D):

    def __init__(self, robot: Robot, *, debug: bool = False):
        super().__init__('group')
        self.robot = robot
        with self:
            with Group() as self.robot_group:
                outline = list(map(list, robot.shape.outline))
                Extrusion(outline, robot.shape.height, wireframe=debug).material('#4488ff', 0.5)
                if debug:
                    Sphere(0.03).material('#4488ff')
                    Sphere(0.05).material('#4488ff').move(robot.parameters.hook_offset)
            with Group() as self.carrot_group:
                Sphere(0.03).material('#ff8800')
                Sphere(0.05).material('#ff8800').move(robot.parameters.carrot_offset)
        self.update()

    def update(self):
        self.robot_group.move(self.robot.prediction.x, self.robot.prediction.y)
        self.robot_group.rotate(0, 0, self.robot.prediction.yaw)
        if self.robot.carrot is None:
            self.carrot_group.scale(0)
        else:
            self.carrot_group.scale(1)
            self.carrot_group.move(self.robot.carrot.x, self.robot.carrot.y)
            self.carrot_group.rotate(0, 0, self.robot.carrot.yaw)