"""Defines the CLI for getting information about robot classes."""

import itertools
import json
import logging
import math
import time
from typing import Sequence

import click
from tabulate import tabulate

from kscale.utils.cli import coro
from kscale.web.clients.robot_class import RobotClassClient
from kscale.web.gen.api import RobotURDFMetadataInput

logger = logging.getLogger(__name__)


class RobotURDFMetadataInputStrict(RobotURDFMetadataInput):
    class Config:
        extra = "forbid"


@click.group()
def cli() -> None:
    """Get information about robot classes."""
    pass


@cli.command()
@coro
async def list() -> None:
    """Lists all robot classes."""
    client = RobotClassClient()
    robot_classes = await client.get_robot_classes()
    if robot_classes:
        # Prepare table data
        table_data = [
            [
                click.style(rc.id, fg="blue"),
                click.style(rc.class_name, fg="green"),
                rc.description or "N/A",
                "N/A" if rc.num_downloads is None else f"{rc.num_downloads:,}",
            ]
            for rc in robot_classes
        ]
        click.echo(tabulate(table_data, headers=["ID", "Name", "Description", "Downloads"], tablefmt="simple"))
    else:
        click.echo(click.style("No robot classes found", fg="red"))


@cli.command()
@click.argument("name")
@click.option("-d", "--description", type=str, default=None)
@coro
async def add(
    name: str,
    description: str | None = None,
) -> None:
    """Adds a new robot class."""
    async with RobotClassClient() as client:
        robot_class = await client.create_robot_class(name, description)
    click.echo("Robot class created:")
    click.echo(f"  ID: {click.style(robot_class.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot_class.class_name, fg='green')}")
    click.echo(f"  Description: {click.style(robot_class.description or 'N/A', fg='yellow')}")


@cli.command()
@click.argument("current_name")
@click.option("-n", "--name", type=str, default=None)
@click.option("-d", "--description", type=str, default=None)
@coro
async def update(current_name: str, name: str | None = None, description: str | None = None) -> None:
    """Updates a robot class."""
    async with RobotClassClient() as client:
        robot_class = await client.update_robot_class(current_name, name, description)
    click.echo("Robot class updated:")
    click.echo(f"  ID: {click.style(robot_class.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot_class.class_name, fg='green')}")
    click.echo(f"  Description: {click.style(robot_class.description or 'N/A', fg='yellow')}")


@cli.command("delete")
@click.argument("name")
@coro
async def delete_robot_class(name: str) -> None:
    """Deletes a robot class."""
    async with RobotClassClient() as client:
        await client.delete_robot_class(name)
    click.echo(f"Robot class deleted: {click.style(name, fg='red')}")


@cli.group()
def metadata() -> None:
    """Handle the robot class metadata."""
    pass


@metadata.command("update")
@click.argument("name")
@click.argument("json_path", type=click.Path(exists=True))
@coro
async def update_metadata(name: str, json_path: str) -> None:
    """Updates the metadata of a robot class."""
    with open(json_path, "r", encoding="utf-8") as f:
        raw_metadata = json.load(f)
    metadata = RobotURDFMetadataInputStrict.model_validate(raw_metadata)
    async with RobotClassClient() as client:
        robot_class = await client.update_robot_class(name, new_metadata=metadata)
    click.echo("Robot class metadata updated:")
    click.echo(f"  ID: {click.style(robot_class.id, fg='blue')}")
    click.echo(f"  Name: {click.style(robot_class.class_name, fg='green')}")


@metadata.command("get")
@click.argument("name")
@click.option("--json-path", type=click.Path(exists=False))
@coro
async def get_metadata(name: str, json_path: str | None = None) -> None:
    """Gets the metadata of a robot class."""
    async with RobotClassClient() as client:
        robot_class = await client.get_robot_class(name)
    metadata = robot_class.metadata
    if metadata is None:
        click.echo(click.style("No metadata found", fg="red"))
        return
    if json_path is None:
        click.echo(metadata.model_dump_json(indent=2))
    else:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f)


@cli.group()
def urdf() -> None:
    """Handle the robot class URDF."""
    pass


@urdf.command("upload")
@click.argument("class_name")
@click.argument("urdf_file")
@coro
async def upload_urdf(class_name: str, urdf_file: str) -> None:
    """Uploads a URDF file to a robot class."""
    async with RobotClassClient() as client:
        response = await client.upload_robot_class_urdf(class_name, urdf_file)
    click.echo("URDF uploaded:")
    click.echo(f"  Filename: {click.style(response.filename, fg='green')}")


@urdf.command("download")
@click.argument("class_name")
@click.option("--cache", is_flag=True, default=False)
@coro
async def download_urdf(class_name: str, cache: bool) -> None:
    """Downloads a URDF file from a robot class."""
    async with RobotClassClient() as client:
        urdf_file = await client.download_and_extract_urdf(class_name, cache=cache)
    click.echo(f"URDF downloaded: {click.style(urdf_file, fg='green')}")


@urdf.command("pybullet")
@click.argument("class_name")
@click.option("--no-cache", is_flag=True, default=False)
@click.option("--hide-gui", is_flag=True, default=False)
@click.option("--hide-origin", is_flag=True, default=False)
@click.option("--see-thru", is_flag=True, default=False)
@click.option("--show-collision", is_flag=True, default=False)
@click.option("--show-inertia", is_flag=True, default=False)
@click.option("--fixed-base", is_flag=True, default=False)
@click.option("--no-merge", is_flag=True, default=False)
@click.option("--dt", type=float, default=0.01)
@click.option("--start-height", type=float, default=0.0)
@click.option("--cycle-duration", type=float, default=2.0)
@coro
async def run_pybullet(
    class_name: str,
    no_cache: bool,
    hide_gui: bool,
    hide_origin: bool,
    see_thru: bool,
    show_collision: bool,
    show_inertia: bool,
    fixed_base: bool,
    no_merge: bool,
    dt: float,
    start_height: float,
    cycle_duration: float,
) -> None:
    """Shows the URDF file for a robot class in PyBullet."""
    try:
        import pybullet as p  # noqa: PLC0415
    except ImportError:
        click.echo(click.style("PyBullet is not installed; install it with `pip install pybullet`", fg="red"))
        return
    async with RobotClassClient() as client:
        urdf_base = await client.download_and_extract_urdf(class_name, cache=not no_cache)
    try:
        urdf_path = next(urdf_base.glob("*.urdf"))
    except StopIteration:
        click.echo(click.style(f"No URDF file found in {urdf_base}", fg="red"))
        return

    # Connect to PyBullet.
    p.connect(p.GUI)
    p.setGravity(0, 0, -9.81)
    p.setRealTimeSimulation(0)

    # Create floor plane
    floor = p.createCollisionShape(p.GEOM_PLANE)
    p.createMultiBody(0, floor)

    # Turn off panels.
    if hide_gui:
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
    p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW, 0)
    p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW, 0)
    p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW, 0)

    # Enable mouse picking.
    p.configureDebugVisualizer(p.COV_ENABLE_MOUSE_PICKING, 1)

    # Load the robot URDF.
    start_position = [0.0, 0.0, start_height]
    start_orientation = p.getQuaternionFromEuler([0.0, 0.0, 0.0])
    flags = p.URDF_USE_INERTIA_FROM_FILE
    if not no_merge:
        flags |= p.URDF_MERGE_FIXED_LINKS

    robot = p.loadURDF(
        str(urdf_path.resolve().absolute()),
        start_position,
        start_orientation,
        flags=flags,
        useFixedBase=fixed_base,
    )

    # Display collision meshes as separate object.
    if show_collision:
        collision_flags = p.URDF_USE_INERTIA_FROM_FILE | p.URDF_USE_SELF_COLLISION_EXCLUDE_ALL_PARENTS
        collision = p.loadURDF(
            str(urdf_path.resolve().absolute()),
            start_position,
            start_orientation,
            flags=collision_flags,
            useFixedBase=0,
        )

        # Make collision shapes semi-transparent.
        joint_ids = [i for i in range(p.getNumJoints(collision))] + [-1]
        for i in joint_ids:
            p.changeVisualShape(collision, i, rgbaColor=[1, 0, 0, 0.5])

    # Initializes physics parameters.
    p.changeDynamics(floor, -1, lateralFriction=1, spinningFriction=-1, rollingFriction=-1)
    p.setPhysicsEngineParameter(fixedTimeStep=dt, maxNumCmdPer1ms=1000)

    # Shows the origin of the robot.
    if not hide_origin:
        p.addUserDebugLine([0, 0, 0], [0.1, 0, 0], [1, 0, 0], parentObjectUniqueId=robot, parentLinkIndex=-1)
        p.addUserDebugLine([0, 0, 0], [0, 0.1, 0], [0, 1, 0], parentObjectUniqueId=robot, parentLinkIndex=-1)
        p.addUserDebugLine([0, 0, 0], [0, 0, 0.1], [0, 0, 1], parentObjectUniqueId=robot, parentLinkIndex=-1)

    # Make the robot see-through.
    joint_ids = [i for i in range(p.getNumJoints(robot))] + [-1]
    if see_thru:
        shape_data = p.getVisualShapeData(robot)
        for i in joint_ids:
            prev_color = shape_data[i][-1]
            p.changeVisualShape(robot, i, rgbaColor=prev_color[:3] + (0.9,))

    def draw_box(pt: Sequence[Sequence[float]], color: tuple[float, float, float], obj_id: int, link_id: int) -> None:
        """Draw a box in PyBullet debug visualization.

        Args:
            pt: List of 8 points defining box vertices, each point is [x,y,z]
            color: RGB color tuple for the box lines
            obj_id: PyBullet object ID to attach box to
            link_id: Link ID on the object to attach box to
        """
        assert len(pt) == 8
        assert all(len(p) == 3 for p in pt)

        p.addUserDebugLine(pt[0], pt[1], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[1], pt[3], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[3], pt[2], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[2], pt[0], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)

        p.addUserDebugLine(pt[0], pt[4], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[1], pt[5], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[2], pt[6], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[3], pt[7], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)

        p.addUserDebugLine(pt[4 + 0], pt[4 + 1], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[4 + 1], pt[4 + 3], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[4 + 3], pt[4 + 2], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)
        p.addUserDebugLine(pt[4 + 2], pt[4 + 0], color, 1, parentObjectUniqueId=obj_id, parentLinkIndex=link_id)

    # Shows bounding boxes around each part of the robot representing the inertia frame.
    if show_inertia:
        for i in joint_ids:
            dynamics_info = p.getDynamicsInfo(robot, i)
            mass = dynamics_info[0]
            if mass <= 0:
                continue
            inertia = dynamics_info[2]

            # Calculate box dimensions.
            ixx, iyy, izz = inertia[0], inertia[1], inertia[2]
            box_scale_x = math.sqrt(6 * (iyy + izz - ixx) / mass) / 2
            box_scale_y = math.sqrt(6 * (ixx + izz - iyy) / mass) / 2
            box_scale_z = math.sqrt(6 * (ixx + iyy - izz) / mass) / 2
            half_extents = [box_scale_x, box_scale_y, box_scale_z]

            # Create box vertices in local inertia frame
            pt = [
                [half_extents[0], half_extents[1], half_extents[2]],
                [-half_extents[0], half_extents[1], half_extents[2]],
                [half_extents[0], -half_extents[1], half_extents[2]],
                [-half_extents[0], -half_extents[1], half_extents[2]],
                [half_extents[0], half_extents[1], -half_extents[2]],
                [-half_extents[0], half_extents[1], -half_extents[2]],
                [half_extents[0], -half_extents[1], -half_extents[2]],
                [-half_extents[0], -half_extents[1], -half_extents[2]],
            ]

            draw_box(pt, (1, 0, 0), robot, i)

    # Show joint controller.
    joints: dict[str, int] = {}
    controls: dict[str, float] = {}
    for i in range(p.getNumJoints(robot)):
        joint_info = p.getJointInfo(robot, i)
        name = joint_info[1].decode("utf-8")
        joint_type = joint_info[2]
        joints[name] = i
        if joint_type == p.JOINT_PRISMATIC:
            joint_min, joint_max = joint_info[8:10]
            controls[name] = p.addUserDebugParameter(name, joint_min, joint_max, 0.0)
        elif joint_type == p.JOINT_REVOLUTE:
            joint_min, joint_max = joint_info[8:10]
            controls[name] = p.addUserDebugParameter(name, joint_min, joint_max, 0.0)

    def reset_joints_to_zero(robot: int, joints: dict[str, int]) -> None:
        for joint_id in joints.values():
            joint_info = p.getJointInfo(robot, joint_id)
            joint_min, joint_max = joint_info[8:10]
            zero_position = (joint_min + joint_max) / 2
            p.setJointMotorControl2(robot, joint_id, p.POSITION_CONTROL, zero_position)

    def reset_camera(position: int) -> None:
        height = start_height if fixed_base else 0
        camera_positions = {
            1: (2.0, 0, -30, [0, 0, height]),  # Default view
            2: (2.0, 90, -30, [0, 0, height]),  # Side view
            3: (2.0, 180, -30, [0, 0, height]),  # Back view
            4: (2.0, 270, -30, [0, 0, height]),  # Other side view
            5: (2.0, 0, 0, [0, 0, height]),  # Front level view
            6: (2.0, 0, -80, [0, 0, height]),  # Top-down view
            7: (1.5, 45, -45, [0, 0, height]),  # Closer angled view
            8: (3.0, 30, -30, [0, 0, height]),  # Further angled view
            9: (2.0, 0, 30, [0, 0, height]),  # Low angle view
        }

        if position in camera_positions:
            distance, yaw, pitch, target = camera_positions[position]
            p.resetDebugVisualizerCamera(
                cameraDistance=distance,
                cameraYaw=yaw,
                cameraPitch=pitch,
                cameraTargetPosition=target,
            )

    # Run the simulation until the user closes the window.
    last_time = time.time()
    prev_control_values = {k: 0.0 for k in controls}
    cycle_joints = False
    cycle_start_time = 0.0

    while p.isConnected():
        # Reset the simulation if "r" was pressed.
        keys = p.getKeyboardEvents()
        if ord("r") in keys and keys[ord("r")] & p.KEY_WAS_TRIGGERED:
            p.resetBasePositionAndOrientation(robot, start_position, start_orientation)
            p.setJointMotorControlArray(
                robot,
                range(p.getNumJoints(robot)),
                p.POSITION_CONTROL,
                targetPositions=[0] * p.getNumJoints(robot),
            )

        # Reset joints to zero position if "z" was pressed
        if ord("z") in keys and keys[ord("z")] & p.KEY_WAS_TRIGGERED:
            reset_joints_to_zero(robot, joints)
            cycle_joints = False  # Stop joint cycling if it was active

        # Reset camera if number keys 1-9 are pressed
        for i in range(1, 10):
            if ord(str(i)) in keys and keys[ord(str(i))] & p.KEY_WAS_TRIGGERED:
                reset_camera(i)

        # Start/stop joint cycling if "c" was pressed
        if ord("c") in keys and keys[ord("c")] & p.KEY_WAS_TRIGGERED:
            cycle_joints = not cycle_joints
            if cycle_joints:
                cycle_start_time = time.time()
            else:
                # When stopping joint cycling, set joints to their current positions
                for k, v in controls.items():
                    current_position = p.getJointState(robot, joints[k])[0]
                    p.setJointMotorControl2(robot, joints[k], p.POSITION_CONTROL, current_position)

        # Set joint positions.
        if cycle_joints:
            elapsed_time = time.time() - cycle_start_time
            cycle_progress = (elapsed_time % cycle_duration) / cycle_duration
            for k, v in controls.items():
                joint_info = p.getJointInfo(robot, joints[k])
                joint_min, joint_max = joint_info[8:10]
                target_position = joint_min + (joint_max - joint_min) * math.sin(cycle_progress * math.pi)
                p.setJointMotorControl2(robot, joints[k], p.POSITION_CONTROL, target_position)
        else:
            for k, v in controls.items():
                try:
                    target_position = p.readUserDebugParameter(v)
                    if target_position != prev_control_values[k]:
                        prev_control_values[k] = target_position
                        p.setJointMotorControl2(robot, joints[k], p.POSITION_CONTROL, target_position)
                except p.error:
                    logger.debug("Failed to set joint %s", k)
                    pass

        # Step simulation.
        p.stepSimulation()
        cur_time = time.time()
        time.sleep(max(0, dt - (cur_time - last_time)))
        last_time = cur_time


@urdf.command("mujoco")
@click.argument("class_name")
@click.option("--scene", type=str, default="smooth")
@click.option("--no-cache", is_flag=True, default=False)
@coro
async def run_mujoco(class_name: str, scene: str, no_cache: bool) -> None:
    """Shows the URDF file for a robot class in Mujoco.

    This command downloads and extracts the robot class URDF folder,
    searches for an MJCF file (unless --mjcf-path is provided), and then
    launches the Mujoco viewer using the provided MJCF file.
    """
    try:
        from mujoco_scenes.errors import TemplateNotFoundError  # noqa: PLC0415
        from mujoco_scenes.mjcf import list_scenes, load_mjmodel  # noqa: PLC0415
    except ImportError:
        click.echo(click.style("Mujoco Scenes is required; install with `pip install mujoco-scenes`", fg="red"))
        return

    try:
        import mujoco.viewer  # noqa: PLC0415
    except ImportError:
        click.echo(click.style("Mujoco is required; install with `pip install mujoco`", fg="red"))
        return

    async with RobotClassClient() as client:
        extracted_folder = await client.download_and_extract_urdf(class_name, cache=not no_cache)

    try:
        mjcf_file = next(
            itertools.chain(
                extracted_folder.glob("*.scene.mjcf"),
                extracted_folder.glob("*.mjcf"),
                extracted_folder.glob("*.xml"),
            )
        )
    except StopIteration:
        click.echo(click.style(f"No MJCF file found in {extracted_folder}", fg="red"))
        return

    mjcf_path_str = str(mjcf_file.resolve())
    click.echo(f"Launching Mujoco viewer with: {click.style(mjcf_path_str, fg='green')}")
    try:
        model = load_mjmodel(mjcf_path_str, scene)
    except TemplateNotFoundError:
        click.echo(click.style(f"Failed to load scene {scene}. Available scenes: {', '.join(list_scenes())}", fg="red"))
        return
    mujoco.viewer.launch(model)


if __name__ == "__main__":
    cli()
