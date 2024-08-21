import os
from pathlib import Path

import argparse
from pathlib import Path
from typing import Any, Dict, Sequence


import os.path as osp

import pybullet_utils.bullet_client as bullet_client
import pybullet_utils.urdfEditor as urdfEditor

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
    elif xml_found:
        return "mjcf"
    else:
        return None


def urdf_to_mjcf(urdf_path: Path, robot_name: str) -> None:
    # Extract the base name from the URDF file path

    # Loading the URDF file and adapting it to the MJCF format
    mjcf_robot = mjcf.Robot(robot_name, urdf_path, mjcf.Compiler(angle="radian", meshdir="meshes"))
    mjcf_robot.adapt_world()

    # Save the MJCF file with the base name
    mjcf_robot.save(urdf_path.parent / f"{robot_name}.xml")


def mjcf_to_urdf(input_mjcf: Path) -> None:
    """Convert an MJCF file to a single URDF file with all parts combined."""

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
    combined_urdf_path = osp.join(output_path, "combined_robot.urdf")

    # Save the combined URDF
    combined_urdf_editor.saveUrdf(combined_urdf_path)

    print(f"Combined URDF saved to: {combined_urdf_path}")