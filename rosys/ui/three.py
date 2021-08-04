import asyncio
from pydantic import BaseModel
from typing import Callable, Optional
import time
from nicegui.elements.custom_view import CustomView
from nicegui.elements.element import Element
from ..world.pose import Pose
from ..world.robot import RobotShape
from ..world.image import Image
from ..world.camera import Camera
from ..world.spline import Spline
from ..world.link import Link


class ThreeView(CustomView):

    def __init__(self, *, on_click: Callable, width: int, height: int):

        super().__init__('three', __file__, ['three.min.js', 'OrbitControls.js'],
                         elements={}, width=width, height=height, follow_robot=True, selected_camera=None)

        self.on_click = on_click
        self.allowed_events = ['onClick']
        self.initialize(temp=False, onClick=self.handle_click)

    def handle_click(self, msg):

        if self.on_click is not None:
            return self.on_click(msg)
        return False


class ThreeElement(BaseModel):

    id: str
    type: str
    pose: Optional[Pose]
    modified: float = 0
    properties: dict = {}


class Three(Element):

    def __init__(self, *, on_click: Callable = None, width: int = 400, height: int = 300):

        super().__init__(ThreeView(on_click=on_click, width=width, height=height))

    def update_follow_robot(self, value: bool):

        if self.view.options.follow_robot == value:
            return False
        self.view.options.follow_robot = value

    def set_robot(self, id: str, pose: Pose, shape: RobotShape):

        element = ThreeElement(id=id, type='robot', pose=pose, properties=shape.dict())
        element.pose.time = 0
        element_dict = element.dict()
        if self.view.options.elements.get(id) == element_dict:
            return False
        self.view.options.elements[id] = element_dict

    def update_images(self, images: list[Image], cameras: dict[str, Camera]):

        dirty = False
        new_images = {image.mac: image for image in images}
        new_image_ids = [image.id for image in new_images.values()]
        old_image_ids = [id for id, e in self.view.options.elements.items() if e['type'] == 'image']
        for id in old_image_ids:
            if id not in new_image_ids:
                del self.view.options.elements[id]
                dirty = True
        for image in new_images.values():
            if image.id not in self.view.options.elements:
                camera = cameras.get(image.mac)
                if camera is not None and camera.projection is not None:
                    properties = image.dict() | {'camera': camera.dict()}
                    jp_element = ThreeElement(id=image.id, type='image', properties=properties)
                    self.view.options.elements[image.id] = jp_element.dict()
                    dirty = True
        return dirty

    async def update_path(self, path: list[Spline]):

        id = 'path'
        path_copy = path.copy()  # NOTE: a shallow copy is enough

        def extract_splines():
            includes = {'start', 'control1', 'control2', 'end'}
            return [spline.dict(include=includes) for spline in path_copy]
        properties = {'splines': await asyncio.get_event_loop().run_in_executor(None, extract_splines)}

        element = ThreeElement(id=id, type='path', properties=properties)
        jp_element = self.view.options.elements.get(id)
        if jp_element is not None and jp_element['properties'] == properties:
            return False
        element.modified = time.time()
        self.view.options.elements[id] = element.dict()

    def update_carrot(self, pose: Pose):

        id = 'carrot'
        element = ThreeElement(id=id, type='carrot', pose=pose)
        if element.pose is not None:
            element.pose.time = 0
        element_dict = element.dict()
        if self.view.options.elements.get(id) == element_dict:
            return False
        self.view.options.elements[id] = element_dict

    def update_cameras(self, cameras: dict[str, Camera]):

        dirty = False
        old_ids = [id for id, e in self.view.options.elements.items() if e['type'] == 'camera']
        for id in old_ids:
            if id.replace('_', '') not in cameras:
                del self.view.options.elements[id]
                dirty = True
        for mac, camera in cameras.items():
            for id, calibration in [(mac, camera.calibration), (mac + '_', camera.calibration_simulation)]:
                jp_element = self.view.options.elements.get(id)
                properties = {'color': [c / 255 for c in camera.color]}
                if calibration:
                    properties |= calibration.dict()
                    if calibration.is_complete:
                        properties['extrinsics']['rotation'] = calibration.rotation.R
                if jp_element is not None and jp_element['properties'] == properties:
                    continue
                element = ThreeElement(id=id, type='camera', modified=time.time(), properties=properties)
                self.view.options.elements[id] = element.dict()
                dirty = True
        return dirty

    def update_links(self, links: list[Link]):

        dirty = False
        old_ids = [id for id, e in self.view.options.elements.items() if e['type'] == 'link']
        new_ids = [f'{link.id}_{link.mac}' for link in links]
        for id in old_ids:
            if id not in new_ids:
                del self.view.options.elements[id]
                dirty = True
        for link in links:
            if link.world_point is None:
                continue
            id = f'{link.id}_{link.mac}'
            pose = Pose(x=link.world_point.x, y=link.world_point.y, yaw=0)
            jp_element = self.view.options.elements.get(id)
            if jp_element is not None and jp_element['pose']['x'] == pose.x and jp_element['pose']['y'] == pose.y:
                continue
            element = ThreeElement(id=id, type='link', pose=pose)
            self.view.options.elements[id] = element.dict()
            dirty = True
        return dirty

    def select_camera(self, mac: str):

        dirty = self.view.options.selected_camera != mac
        self.view.options.selected_camera = mac
        return dirty
