import pytest
import numpy as np
from tests.helper import assert_pose, drive


@pytest.mark.asyncio
async def test_drive(world):
    assert_pose(0, 0, yaw_deg=0)

    await world.simulate(seconds=1.0)
    assert_pose(0, 0, yaw_deg=0)

    drive(1.0)
    await world.simulate(seconds=1.0)
    assert_pose(1.0, 0, yaw_deg=0)

    drive(0.0, deg_per_s=90)
    await world.simulate(seconds=0.5)
    assert_pose(1.0, 0, yaw_deg=45)

    drive(1.0)
    await world.simulate(seconds=np.sqrt(2))
    assert_pose(2.0, 1.0, yaw_deg=45, linear_tolerance=0.1)