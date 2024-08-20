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
    # Set output_path to the directory of the input_mjcf file
    output_path = input_mjcf.parent

    client = bullet_client.BulletClient()
    objs: Dict[int, Any] = client.loadMJCF(str(input_mjcf), flags=client.URDF_USE_IMPLICIT_CYLINDER)

    for obj in objs:
        humanoid = objs[obj]
        ue = urdfEditor.UrdfEditor()
        ue.initializeFromBulletBody(humanoid, client._client)
        robot_name: str = str(client.getBodyInfo(obj)[1], "utf-8")
        part_name: str = str(client.getBodyInfo(obj)[0], "utf-8")
        save_visuals: bool = False
        outpath: str = osp.join(output_path, "{}_{}.urdf".format(robot_name, part_name))
        ue.saveUrdf(outpath, save_visuals)
