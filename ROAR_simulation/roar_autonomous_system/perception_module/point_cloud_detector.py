from ROAR_simulation.roar_autonomous_system.perception_module.detector import Detector
import logging
import open3d as o3d
import numpy as np
import cv2
import time
from typing import Optional


class PointCloudDetector(Detector):
    def __init__(self, max_detectable_distance=0.1, depth_scaling_factor=1000, **kwargs):
        """

        Args:
            max_detectable_distance: maximum detectable distance in km
            depth_scaling_factor: scaling depth back to world scale. 1000 m = 1 km
            **kwargs:
        """
        super().__init__(**kwargs)
        self.max_detectable_distance = max_detectable_distance
        self.depth_scaling_factor = depth_scaling_factor
        self.logger = logging.getLogger("Point Cloud Detector")
        self.pcd: o3d.geometry.PointCloud = o3d.geometry.PointCloud()
        self.vis = o3d.visualization.Visualizer()

        self.counter = 0

    def run_step(self) -> Optional[np.ndarray]:
        points_3d = self.calculate_world_cords(max_points_to_convert=10000)

        # print(np.amin(points_3d, axis=1), np.amax(points_3d, axis=1), self.agent.vehicle.transform.location)
        # self.pcd.points = o3d.utility.Vector3dVector(points_3d.T - np.mean(points_3d.T, axis=0))
        # self.pcd.paint_uniform_color([0,0,0])
        # points_3d = points_3d.T
        # # filter out anything that is "above" my vehicle (so ground is definitely below my vehicle)
        # # this part is shady, idk why it works
        # ground_indicies = np.where(points_3d[:, 0] > self.agent.vehicle.transform.location.to_array()[0])
        # ground_points = points_3d[ground_indicies]
        # print(np.shape(ground_points.T))
        # self.pcd.points = o3d.utility.Vector3dVector(ground_points.T)
        #
        # # # find the normals using Open3D
        # self.pcd.points = o3d.utility.Vector3dVector(ground_points - np.mean(ground_points, axis=0))
        # print(self.pcd.get_min_bound(), self.pcd.get_max_bound())
        # self.pcd.estimate_normals(fast_normal_computation=True)
        #
        # # find normals that are less than the mean normal,
        # # since I know that most of the things in front of me are going to be ground
        # normals = np.asarray(self.pcd.normals)
        # abs_diff = np.linalg.norm(normals - np.mean(normals, axis=0), axis=1)
        # ground_loc = np.where(abs_diff < np.mean(abs_diff))
        # ground = ground_points[ground_loc[0]]
        #
        # # turn it into Open3D PointCloud object again to utilize its remove outlier method
        # # this is when I drive to the side, the opposing road will be recognized, but we don't want that
        # self.pcd.points = o3d.utility.Vector3dVector(ground)
        # new_pcd, indices = self.pcd.remove_radius_outlier(100, 2)

        # project it back to Open3D PointCloud object for visualizations
        # minus the mean for stationary visualization
        # # self.pcd.points = o3d.utility.Vector3dVector(ground[indices])
        # if self.counter == 0:
        #     self.vis.create_window(window_name="Open3d", width=400, height=400)
        #     self.vis.add_geometry(self.pcd)
        #     render_option: o3d.visualization.RenderOption = self.vis.get_render_option()
        #     render_option.show_coordinate_frame = True
        # else:
        #     self.vis.update_geometry(self.pcd)
        #     render_option: o3d.visualization.RenderOption = self.vis.get_render_option()
        #     render_option.show_coordinate_frame = True
        #     self.vis.poll_events()
        #     self.vis.update_renderer()
        # self.counter += 1
        return points_3d

    def calculate_world_cords(self, max_points_to_convert=5000):
        depth_img = self.agent.front_depth_camera.data.copy()
        depth_img[depth_img > 0.05] = 0
        depth_img = depth_img * 1000
        # create a n x 2 array
        img_pos = np.indices((depth_img.shape[0], depth_img.shape[1])).transpose(1,2,0)
        img_pos = np.reshape(a=img_pos, newshape=(img_pos.shape[0] * img_pos.shape[1], 2))
        depth_array = np.reshape(a=depth_img, newshape=(depth_img.shape[0] * depth_img.shape[1], 1))

        # print(self.agent.front_depth_camera.data[0][0], self.agent.front_depth_camera.data[0][2])

        """
        [[x,y, depth]]
        """
        # indicies = np.random.choice(a=len(img_pos), size=max_points_to_convert, replace=False)

        # selected_depth_array = depth_array[indicies, :]
        # selected_img_pos = img_pos[indicies, :] * selected_depth_array
        selected_depth_array = depth_array
        selected_img_pos = img_pos * selected_depth_array
        #
        raw_p2d = np.append(selected_img_pos, selected_depth_array, axis=1)

        #
        # raw_p2d = raw_p2d[raw_p2d[:, 2] > 0]
        # raw_p2d = raw_p2d[raw_p2d[:, 2] < 20]
        #
        # # convert to cords_y_minus_z_x
        cords_y_minus_z_x = np.linalg.inv(self.agent.front_depth_camera.intrinsics_matrix) @ raw_p2d.T
        # #
        # # convert to cords_xyz_1 -y,x-z
        cords_xyz_1 = np.vstack([
            -cords_y_minus_z_x[0, :],
            cords_y_minus_z_x[2, :],
            -cords_y_minus_z_x[1, :],
            np.ones((1, np.shape(cords_y_minus_z_x)[1]))
        ])
        print(self.agent.vehicle.transform)
        self.agent.vehicle.transform.rotation.roll = 90  #-self.agent.vehicle.transform.rotation.roll
        # self.agent.vehicle.transform.rotation.pitch = 90
        self.agent.vehicle.transform.rotation.yaw = -self.agent.vehicle.transform.rotation.yaw
        # # print(self.agent.front_depth_camera.transform)
        # # self.agent.front_depth_camera.transform.rotation.roll = -self.agent.front_depth_camera.transform.rotation.roll
        # # self.agent.front_depth_camera.transform.rotation.pitch = -self.agent.front_depth_camera.transform.rotation.pitch
        # self.agent.front_depth_camera.transform.rotation.yaw = -self.agent.front_depth_camera.transform.rotation.yaw
        #
        points = self.agent.vehicle.transform.get_matrix() @ \
                 self.agent.front_depth_camera.transform.get_matrix() @ cords_xyz_1
        return points[:3, :]
