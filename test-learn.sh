for learner in 0 1
do
    for experiment in 5 8 #0 2 4 6 9 10
    do
        for trial in 5 6 7 8 9 10
        do
            python test-learn.py $learner $experiment $trial > big3/transcripts/$learner-$experiment-$trial.txt &
        done
    done

    #for experiment in 1 3 7 
    #do
    #    python test-learn.py $learner $experiment 0  > big/transcripts/$learner-$experiment-0.txt &
    #done
done