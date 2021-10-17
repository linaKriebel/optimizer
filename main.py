import sys

import collector
import dbconnector
import minimizer 
import bmconnector

if __name__ == "__main__":

    ORDER = 173
    HOSTNAME = "qa30.plunet.com"

    # parse arguments [scriptname, order, host]
    if len(sys.argv) > 1:
        ORDER = sys.argv[1]
        HOSTNAME = sys.argv[2]

    # get data from database
    print("### fetch data from database")
    data = collector.get_data(ORDER)

    iso = dbconnector.is_iso_active(ORDER)
    target = dbconnector.is_target_profit_margin_active()

    # call minizinc
    print("### start optimization")
    result = minimizer.solve(data, iso, target, 10)
    print(result)

    # connect to bm
    bmconnector.login(HOSTNAME)

    if result:
        # parse minizinc result
        for i in range(data.m):
            round_id = dbconnector.get_current_round(data.jobs[i])
            resource_id = data.resources[result["assigned"][i]-1]

            # send results to bm
            status = bmconnector.set_resource(resource_id, round_id)
            print(status)

    # TODO give some useful statistics to the user   
