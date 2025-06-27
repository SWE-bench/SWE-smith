#!/bin/bash

swesmith train traj_mgr clean_trajs trajectories/

swesmith train traj_mgr combine_trajs

swesmith train traj_mgr transform_to_ft