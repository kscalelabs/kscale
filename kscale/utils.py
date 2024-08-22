"""Utility functions for the kscale package."""

import os
from pathlib import Path
from typing import Any, Dict

from kscale.formats import mjcf


def contains_urdf_or_mjcf(folder_path: Path) -> str:
    urdf_found = False
    xml_found = False

    for file in folder_path.iterdir():
        if file.suffix == ".urdf":
            urdf_found = True
        elif file.suffix == ".xml":
            xml_found = True

    if urdf_found:
        return "urdf"
    if xml_found:
        return "mjcf"
    raise ValueError("No URDF or MJCF files found in the folder.")


def urdf_to_mjcf(urdf_path: Path, robot_name: str) -> None:
    # Extract the base name from the URDF file path

    # Loading the URDF file and adapting it to the MJCF format
    mjcf_robot = mjcf.Robot(robot_name, urdf_path, mjcf.Compiler(angle="radian", meshdir="meshes"))
    mjcf_robot.adapt_world()

    # Save the MJCF file with the base name
    mjcf_robot.save(urdf_path.parent / f"{robot_name}.xml")


def mjcf_to_urdf(input_mjcf: Path, name: str = "robot.urdf") -> Path:
    """Convert an MJCF file to a single URDF file with all parts combined.

    Args:
        input_mjcf: The path to the input MJCF file.
        name: The name of the output URDF file.

    Returns:
        The path to the output URDF file.
    """
    try:
        from pybullet_utils import bullet_client, urdfEditor  # type: ignore[import-not-found]
    except ImportError:
        raise ImportError("To use PyBullet, do `pip install 'kscale[pybullet]'`.")

    # Set output_path to the directory of the input MJCF file
    output_path = input_mjcf.parent

    # Initialize the Bullet client
    client = bullet_client.BulletClient()

    # Load the MJCF model
    objs: Dict[int, Any] = client.loadMJCF(str(input_mjcf), flags=client.URDF_USE_IMPLICIT_CYLINDER)

    # Initialize a single URDF editor to store all parts
    combined_urdf_editor = urdfEditor.UrdfEditor()

    # Iterate over all objects in the MJCF model
    for obj in objs:
        humanoid = obj  # Get the current object
        part_urdf_editor = urdfEditor.UrdfEditor()
        part_urdf_editor.initializeFromBulletBody(humanoid, client._client)

        # Add all links from the part URDF editor to the combined editor
        for link in part_urdf_editor.urdfLinks:
            if link not in combined_urdf_editor.urdfLinks:
                combined_urdf_editor.urdfLinks.append(link)

        # Add all joints from the part URDF editor to the combined editor
        for joint in part_urdf_editor.urdfJoints:
            if joint not in combined_urdf_editor.urdfJoints:
                combined_urdf_editor.urdfJoints.append(joint)

    # Set the output path for the combined URDF file
    combined_urdf_path = os.path.join(output_path, name)

    # Save the combined URDF
    combined_urdf_editor.saveUrdf(combined_urdf_path)

    return Path(combined_urdf_path)
