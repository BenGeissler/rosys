import copy

import numpy as np

from rosys.geometry import Point3d
from rosys.testing import approx
from rosys.vision import CalibratableCamera, Calibration
from rosys.vision.calibration import CameraModel


def demo_data() -> tuple[CalibratableCamera, list[Point3d]]:
    cam = CalibratableCamera(id='1')
    cam.set_perfect_calibration(x=0.1, y=0.2, z=3, roll=np.deg2rad(180+10), pitch=np.deg2rad(20), yaw=np.deg2rad(30))
    world_points = [
        Point3d(x=x, y=y, z=z)
        for x in [-1.0, 0.0, 1.0]
        for y in [-1.0, 0.0, 1.0]
        for z in [-1.0, 0.0, 1.0]
    ]
    return cam, world_points


def demo_fisheye_data() -> tuple[CalibratableCamera, list[Point3d]]:
    cam = CalibratableCamera(id='1')
    cam.set_perfect_calibration(width=800, height=600, x=0.1, y=0.2, z=3,
                                roll=np.deg2rad(180+10), pitch=np.deg2rad(20), yaw=np.deg2rad(30))
    assert cam.calibration and cam.calibration.intrinsics
    cam.calibration.intrinsics.distortion = [0.1, 0.4, -0.5, 0.2]
    cam.calibration.intrinsics.model = CameraModel.FISHEYE
    world_points = [
        Point3d(x=x, y=y, z=z)
        for x in [-2.0, -0.5, 0.0, 0.5, 2.0]
        for y in [-1.0, -0.5, 0.0, 0.5, 1.0]
        for z in [-1.0, 0.0, 1.0]
    ]
    return cam, world_points


def demo_omnidirectional_data() -> tuple[CalibratableCamera, list[Point3d]]:
    cam = CalibratableCamera(id='1')
    cam.set_perfect_calibration(width=800, height=600, focal_length=700,
                                x=0.1, y=0.2, z=3,
                                roll=np.deg2rad(180+10), pitch=np.deg2rad(5), yaw=np.deg2rad(30))
    assert cam.calibration and cam.calibration.intrinsics
    cam.calibration.intrinsics.distortion = [-0.3, 0.06, -0.001, 0.0002]
    cam.calibration.intrinsics.xi = 0.7
    cam.calibration.intrinsics.model = CameraModel.OMNIDIRECTIONAL

    world_points = [Point3d(x=x, y=y, z=1)
                    for x in np.linspace(-3.0, 3.0, 8)
                    for y in np.linspace(-3.0, 3.0, 8)
                    ]
    return cam, world_points


def test_calibration_from_points():
    cam, world_points = demo_data()
    image_size = cam.calibration.intrinsics.size

    image_points = [cam.calibration.project_to_image(p) for p in world_points]
    assert not any(p is None for p in image_points)
    focal_length = cam.calibration.intrinsics.matrix[0][0]
    calibration = Calibration.from_points(world_points, image_points, image_size, focal_length)

    approx(calibration.intrinsics.matrix, cam.calibration.intrinsics.matrix)
    approx(calibration.intrinsics.rotation.R, cam.calibration.intrinsics.rotation.R)
    approx(calibration.extrinsics.translation, cam.calibration.extrinsics.translation)
    approx(calibration.extrinsics.rotation.R, cam.calibration.extrinsics.rotation.R, abs=1e-6)


def test_fisheye_calibration_from_points():
    cam, world_points = demo_fisheye_data()
    image_size = cam.calibration.intrinsics.size

    image_points = [cam.calibration.project_to_image(p) for p in world_points]
    assert not any(p is None for p in image_points)
    focal_length = cam.calibration.intrinsics.matrix[0][0]
    calibration = Calibration.from_points(world_points, image_points, image_size,
                                          focal_length, camera_model=CameraModel.FISHEYE)

    approx(calibration.intrinsics.matrix, cam.calibration.intrinsics.matrix)
    approx(calibration.intrinsics.rotation.R, cam.calibration.intrinsics.rotation.R)
    approx(calibration.extrinsics.translation, cam.calibration.extrinsics.translation)
    approx(calibration.extrinsics.rotation.R, cam.calibration.extrinsics.rotation.R, abs=1e-6)


def test_omnidirectional_calibration_from_points():
    cam, world_points = demo_omnidirectional_data()
    image_size = cam.calibration.intrinsics.size

    def translated_calibrations(base_calibration: Calibration, n=6):
        for dz in np.linspace(0, 4, n):
            calibration = copy.deepcopy(base_calibration)
            calibration.extrinsics.translation[2] += dz
            yield calibration

    n_views = 10

    image_points = [[calib.project_to_image(p) for p in world_points]
                    for calib in translated_calibrations(cam.calibration, n_views)]
    world_points = [world_points for _ in range(n_views)]
    assert not any(p is None for view in image_points for p in view)
    focal_length = cam.calibration.intrinsics.matrix[0][0]
    calibration = Calibration.from_points(world_points, image_points, image_size,
                                          focal_length, camera_model=CameraModel.OMNIDIRECTIONAL)

    new_image_points = [calibration.project_to_image(p) for p in world_points[0]]
    rms = np.mean([np.linalg.norm((p - p_).tuple) for p, p_ in zip(image_points[0], new_image_points)])
    approx(rms, 0, abs=1e-1)
    approx(calibration.extrinsics.rotation.R, cam.calibration.extrinsics.rotation.R, abs=1e-3)
    approx(calibration.extrinsics.translation, cam.calibration.extrinsics.translation, abs=1e-3)
    approx(calibration.intrinsics.rotation.R, cam.calibration.intrinsics.rotation.R, abs=1e-3)
    approx(calibration.intrinsics.matrix, cam.calibration.intrinsics.matrix, abs=1e-1)
    approx(calibration.intrinsics.xi, cam.calibration.intrinsics.xi, abs=1e-1)


def test_projection():
    cam, world_points = demo_data()
    for world_point in world_points:
        image_point = cam.calibration.project_to_image(world_point)
        assert image_point is not None
        world_point_ = cam.calibration.project_from_image(image_point, target_height=world_point.z)
        assert np.allclose(world_point.tuple, world_point_.tuple, atol=1e-6)


def test_fisheye_projection():
    cam, world_points = demo_fisheye_data()
    for world_point in world_points:
        image_point = cam.calibration.project_to_image(world_point)
        assert image_point is not None
        world_point_ = cam.calibration.project_from_image(image_point, target_height=world_point.z)
        assert np.allclose(world_point.tuple, world_point_.tuple, atol=1e-6)


def test_omnidirectional_projection():
    cam, world_points = demo_omnidirectional_data()

    for world_point in world_points:
        image_point = cam.calibration.project_to_image(world_point)
        assert image_point is not None
        world_point_ = cam.calibration.project_from_image(image_point, target_height=world_point.z)
        assert np.allclose(world_point.tuple, world_point_.tuple, atol=1e-6)


def test_array_projection():
    cam, world_points = demo_data()
    world_points = [p for p in world_points if p.z == 1]

    world_point_array = np.array([p.tuple for p in world_points])
    image_point_array = cam.calibration.project_to_image(world_point_array)
    for i, world_point in enumerate(world_points):
        image_point = cam.calibration.project_to_image(world_point)
        assert np.allclose(image_point.tuple, image_point_array[i])  # pylint: disable=unsubscriptable-object
    world_point_array_ = cam.calibration.project_from_image(image_point_array, target_height=1)
    assert np.allclose(world_point_array, world_point_array_, atol=1e-6)


def test_fisheye_array_projection():
    cam, world_points = demo_fisheye_data()
    world_points = [p for p in world_points if p.z == 1]

    world_point_array = np.array([p.tuple for p in world_points])
    image_point_array = cam.calibration.project_to_image(world_point_array)
    for i, world_point in enumerate(world_points):
        image_point = cam.calibration.project_to_image(world_point)
        assert np.allclose(image_point.tuple, image_point_array[i])  # pylint: disable=unsubscriptable-object
    world_point_array_ = cam.calibration.project_from_image(image_point_array, target_height=1)
    assert np.allclose(world_point_array, world_point_array_, atol=1e-6)


def test_omnidirectional_array_projection():
    cam, world_points = demo_omnidirectional_data()
    world_points = [p for p in world_points if abs(p.z) <= 1]

    world_point_array = np.array([p.tuple for p in world_points])
    image_point_array = cam.calibration.project_to_image(world_point_array)
    for i, world_point in enumerate(world_points):
        image_point = cam.calibration.project_to_image(world_point)
        assert image_point is not None
        assert np.allclose(image_point.tuple, image_point_array[i])  # pylint: disable=unsubscriptable-object
    world_point_array_ = cam.calibration.project_from_image(image_point_array, target_height=1)
    assert np.allclose(world_point_array, world_point_array_, atol=1e-6)


def test_project_from_behind():
    cam = CalibratableCamera(id='1')
    cam.set_perfect_calibration(z=1, roll=np.deg2rad(180 + 10))
    assert cam.calibration.project_to_image(Point3d(x=0, y=1, z=1)) is not None
    assert cam.calibration.project_to_image(Point3d(x=0, y=-1, z=1)) is None


def test_fisheye_project_from_behind():
    cam = CalibratableCamera(id='1')
    cam.set_perfect_calibration(z=1, roll=np.deg2rad(180 + 10))
    cam.calibration.intrinsics.distortion = [0.1, 0.2, 0.3, 0.4]
    cam.calibration.intrinsics.model = CameraModel.FISHEYE
    assert cam.calibration.project_to_image(Point3d(x=0, y=1, z=1)) is not None
    assert cam.calibration.project_to_image(Point3d(x=0, y=-1, z=1)) is None


def test_omnidirectional_project_from_behind():
    cam = CalibratableCamera(id='1')
    cam.set_perfect_calibration(z=1, roll=np.deg2rad(180 + 10))
    cam.calibration.intrinsics.distortion = [0.1, 0.2, 0.3, 0.4]
    cam.calibration.intrinsics.xi = 0.8
    cam.calibration.intrinsics.model = CameraModel.OMNIDIRECTIONAL
    assert cam.calibration.project_to_image(Point3d(x=0, y=1, z=1)) is not None
    assert cam.calibration.project_to_image(Point3d(x=0, y=-1, z=1)) is not None
