from minizinc import Instance, Model, Solver, Status

from data_collector import AssignmentData

def get_lowest(targets, lowest):
    l = 100
    index = 0
    for i, value in enumerate(targets):
        if value < l and value > lowest: 
            l = value
            index = i
    return index

def add_data(instance, data: AssignmentData):
    instance["n"] = data.n
    instance["m"] = data.m
    instance["k"] = data.k
    instance["l"] = data.l
    instance["profit"] = data.profit
    instance["item_targets"] = data.item_targets
    instance["target"] = data.target
    instance["target_weights"] = data.target_weights
    instance["ranking_weights"] = data.ranking_weights
    instance["jobtype"] = data.jobtype
    instance["workflow"] = data.workflow
    instance["item"] = data.item
    instance["ranking"] = data.ranking
    instance["price"] = data.price
    instance["schedule"] = data.schedule
    instance["planned"] = data.planned

def opt(model, solver, data, objective):
    
    instance = Instance(solver, model)
    add_data(instance, data)

    instance.add_string(objective)
    result = instance.solve()

    if result.status == Status.OPTIMAL_SOLUTION:
        return round(result.objective) # cast to int values
    else:
        print(f"###### {result.status}! no solution found for '{objective}'")

def solve(data, iso, target_active, steps):

    model = Model("assign.mzn")
    
    gecode = Solver.lookup("gecode") # CP solver (not sufficient for float objectives)
    cbc = Solver.lookup("cbc") # MIP solver
    
    instance = Instance(cbc, model)

    # create objective string
    print("##### create normalized weighted sum objective")
    objective = "constraint obj = "

    for i in range(1,data.k+1):

        # search for optimal values of individual objectives (goal programming approach)
        opt_costs = opt(model, cbc, data, f"obj = costs[{i}];")
        opt_quality = opt(model, cbc, data, f"obj = quality[{i}];")

        objective += f"({data.target_weights[i-1]}*(costs[{i}]-{opt_costs}) + {data.ranking_weights[i-1]}*(quality[{i}]-{opt_quality})) + "   

    opt_parallel = opt(model, cbc, data, "obj = parallel_violations;")
    opt_capacity = opt(model, cbc, data, "obj = capacity_violations;")

    objective += f"parallel_violations-{opt_parallel} + capacity_violations-{opt_capacity};"

    instance.add_string(objective)

    if iso:
        # add ISO 17100 constraint to model instance
        print("##### add iso constraint")
        instance.add_string(
            """
            % ISO 17100: a TRA followed by a REV cannot be done by the same resource
            constraint forall(j1 in JOB) (
                forall(j2 in workflow[j1]) (
                    (jobtype[j1] = TRA /\ jobtype[j2] = REV) -> assigned[j1] != assigned[j2]
                )
            ); 
            """
        )

    if target_active:
        # add item target profit margin constraint to model instance
        print("##### add target profit margin constraint")
        instance.add_string(
            """
            % target margin for each item must be met
            constraint forall(i in ITEM)(margin[i] >= item_targets[i]);
            """
        )

    # save a copy of the original item target profit margins
    targets = data.item_targets[:]

    index = 0 # index of the currently lowest weighted item target profit margin
    lowest = 0 # currently lowest weighted item target profit margin
    
    c = 0
    count = 0
    status = Status.UNSATISFIABLE
    print("##### start searching for optimal solution")
    while status == Status.UNSATISFIABLE:

        # TODO terminate after x iterations
        if count > 100:
            break

        with instance.branch() as child:

            # TODO THIS WOULD BE GREAT FOR ML!!! was mach ein PM, wenn die Ziele nicht erreicht werden können
            # TODO rausfinden, wie man hier am besten vorgeht, damit man eine Lösung findet! hard-constraints relaxen

            # after the first failed attempt
            if count > 0:

                if c % steps == 0:
                    # find the items with the next lowest weighted target profit margin
                    index = get_lowest(data.target_weights, lowest)
                    lowest = data.target_weights[index]
                    # reset item target profit margins to original
                    data.item_targets = targets[:]
                    c = 0
                
                # reduce target profit margin by 1% each time
                data.item_targets[index] = targets[index] - c/100

            add_data(child, data)

            # try to solve the COP with the new target profit margins
            result = child.solve()
            status = result.status
        
        c += 1
        count += 1
    
    # TODO return result as custom object
    print("### solution found after {} attempts: {}".format(count, result.status))
    print("#################################################")
    print(result.statistics["time"])
    print("#################################################")
    return(result)
