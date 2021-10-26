import sys
import logging

import collector
import dbconnector
import minimizer 
import bmconnector

if __name__ == "__main__":

    ORDER = 173
    HOSTNAME = "qa30.plunet.com"

    logging.basicConfig(filename='logger.log', format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%y %H:%M:%S', level=logging.INFO)

    # parse arguments [scriptname, order, host]
    if len(sys.argv) > 1:
        ORDER = sys.argv[1]
        HOSTNAME = sys.argv[2]

    # get data from database
    logging.info("Start collecting data from database")
    data = collector.get_data(ORDER)
    logging.info("Finished collecting data from database")

    iso = dbconnector.is_iso_active(ORDER)
    target = dbconnector.is_target_profit_margin_active()

    # call minizinc
    logging.info("Start optimization process")
    result = minimizer.solve(data, iso, target, 10)

    # connect to bm
    bmconnector.login(HOSTNAME)

    if result.satisfiable:
        for i in range(data.m):
            round_id = dbconnector.get_current_round(data.jobs[i])
            resource_id = data.resources[result.assignment[i]-1] # minizinc index 1..n vs. 0..n-1

            # send results to bm
            bmconnector.set_resource(resource_id, round_id)
        


        # TODO give some useful statistics to the user
        # status = bmconnector.set_note(item_id, statistics)
        # if status == 'OK':
        #     logging.info(f"Statistics successfully updated for item {item_id}.")
        # else:
        #     logging.warning(f"A problem occurred while updating statistics for item {item_id}: {status}")
    
    else:
        print(result.message)
        for i in result.items:
            print(i)

        logging.info(f"No solution found!")

       
