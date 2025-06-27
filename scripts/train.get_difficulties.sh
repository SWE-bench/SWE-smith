#!/bin/bash

swesmith train difficulty_rater get_difficulties \
    --base_url https://ylok22798a8ebw.r15.modal.host \
    --dataset_path logs/experiments/exp32__ig_v2_n1.json
    # --dataset_path ../swe_gym_instances_solved.json
