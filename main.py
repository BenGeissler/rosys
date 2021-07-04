#!/usr/bin/env python3
from nicegui import ui
import os
import base64
from rosys.runtime import Runtime
from rosys.world.mode import Mode
from rosys.ui.joystick import Joystick
from rosys.ui.three import Three

import icecream
icecream.install()

has_esp = os.path.exists('/dev/esp') and os.stat('/dev/esp').st_gid > 0
runtime = Runtime(Mode.REAL if has_esp else Mode.SIMULATION)
#runtime = Runtime(Mode.SIMULATION)

with ui.card():

    state = ui.label()
    ui.timer(0.1, lambda: state.set_text(f'''
        {runtime.world.time:.3f} s
        (x={runtime.world.robot.pose.x:.3f},
        y={runtime.world.robot.pose.y:.3f})
    '''))

    Joystick(size=50, color='blue', steerer=runtime.steerer)
    three = Three(runtime.world.robot.pose)
    ui.timer(0.05, lambda: three.set_robot_pose(runtime.world.robot.pose))

with ui.card().style('width:600px'):

    ui.button('Download images', on_click=lambda: runtime.world.download_queue.extend(runtime.world.cameras.keys()))

    with ui.image() as ui_image:
        ui_image.id = None
        svg = ui.svg().style('background:transparent')

    def update_camera_images():

        three.update_images(runtime.world.images, runtime.world.image_data, runtime.world.cameras)

        if not any(runtime.world.images):
            return False

        image = runtime.world.images[-1]

        data = runtime.world.image_data.get(image.id)
        if data is None:
            return False

        if image.detections is None:
            return False

        if ui_image.id == image.id:
            return False

        encoded = base64.b64encode(data).decode("utf-8")
        ui_image.source = 'data:image/jpeg;base64,' + encoded
        ui_image.id = image.id
        ic(image.detections)
        svg_content = '<svg viewBox="0 0 1600 1200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">'
        for d in image.detections:
            svg_content += f'<rect x="{d.x}" y="{d.y}" width="{d.width}" height="{d.height}" stroke="red" fill="red" fill-opacity="10%" />'
            c = {
                'dirt': 'D',
                'robot': 'R',
                'person': 'P',
                'marker_vorne': 'v',
                'marker_mitte': 'm',
                'marker_hinten_links': 'l',
                'marker_hinten_rechts': 'r',
            }.get(d.category_name) or ''
            svg_content += f'<text x="{d.x+2}" y="{d.y+d.height-2}" fill="red">{c}</text>'
        svg_content += '</svg>'
        svg.content = svg_content

    ui.timer(1.0, update_camera_images)

with ui.card():

    ui.label('Cameras')

    cams = ui.label()
    ui.timer(1, lambda: cams.set_text(f'cams: {runtime.world.cameras}'))

    def set_height(height):
        for camera in runtime.world.cameras.values():
            try:
                camera.calibration.extrinsics.translation[2] = height
                camera.projection = None
            except AttributeError:
                pass

    ui.number('Height [m]', on_change=lambda e: set_height(e.value))

ui.on_startup(runtime.run())
ui.on_shutdown(runtime.stop())
