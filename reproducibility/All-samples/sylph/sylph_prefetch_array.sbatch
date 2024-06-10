#!/usr/bin/env bash
#SBATCH --job-name=prefetch
#SBATCH --output=/FIX_PATH/o/%a.o
#SBATCH --error=/FIX_PATH/e/%a.e
#SBATCH --mem=1G
#SBATCH --time=300
#SBATCH --cpus-per-task=1
#SBATCH --signal=B:SIGUSR1@60
#SBATCH --array=1-1000%40

start_time=$(date +"%Y-%m-%dT%H:%M:%S")
start_seconds=$(date +%s)

end_time=RUNNING
exit_code=UNKNOWN

gather_stats() {
# unset the trap otherwise this function can get called more than once
trap - EXIT SIGUSR1
end_time=$(date +"%Y-%m-%dT%H:%M:%S")
end_seconds=$(date +%s)
wall_clock_s=$(($end_seconds-$start_seconds))
echo -e "SLURM_STATS_BEGIN
SLURM_STATS	job_id	$SLURM_JOB_ID
SLURM_STATS	command	/FIX_PATH/prefetch_array_job.sh
SLURM_STATS	requested_ram	1.0
SLURM_STATS	requested_time	240
SLURM_STATS	job_name	prefetch
SLURM_STATS	start_time	$start_time
SLURM_STATS	end_time	$end_time
SLURM_STATS	wall_clock_s	$wall_clock_s
SLURM_STATS	exit_code	$exit_code"
slurmzy jobinfo $SLURM_JOB_ID |  awk '{print "SLURM_STATS_JOBINFO	"$0}'

exit 0

#if [ $exit_code = "UNKNOWN" ]
#then
#    exit 1
#else
#    exit $exit_code
#fi
}

trap gather_stats EXIT SIGUSR1

/usr/bin/time -a -o /FIX_PATH/o/$SLURM_ARRAY_TASK_ID.o -v $SHELL -c "$(cat << 'EOF'
/FIX_PATH/prefetch_array_job.sh
EOF
)"

exit_code=$?
gather_stats

