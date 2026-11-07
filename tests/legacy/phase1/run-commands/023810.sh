S=<SESSION_TEMP_FOLDER>/scratchpad; cd $S; (SCOUT_TEST_MODEL=opus python3 -I $S/run_matrix.py $S/plugin $S/fixture $S/runs-r2-opus --only P1,P2,P3,P4,P6,P8 --conds B,D,E --jobs 3 > $S/runs-r2-opus.log 2>&1) & (python3 -I $S/run_matrix.py $S/plugin $S/fixture $S/runs-r2-default-rep2 --only P1,P2,P3,P4,P5,P7,P8 --conds B,D,E --jobs 3 > $S/runs-r2-default-rep2.log 2>&1) & wait

#### RESULT (is_error=False)
Command running in background with ID: bqq8xfjqy. Output is being written to: <SESSION_TEMP_FOLDER>/tasks/bqq8xfjqy.output. You will be notified when it completes. To check interim output, use Read on that file path.
Session cwd remains /home/claude; directory changes made by the backgrounded command do not apply to subsequent commands.