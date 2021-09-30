import json
from minizinc import Instance, Model, Solver, Status

def get_lowest(targets, lowest):
    l = 100
    index = 0
    for i, value in enumerate(targets):
        if value < l and value > lowest: 
            l = value
            index = i
    return index

def normalize(model, solver, items):

    instance = Instance(solver, model)
    instance.add_file("./data.json")

    norm = dict.fromkeys(items, {})

    for i in items:

        # costs
        with instance.branch() as child:

            child.add_string("obj = costs[{}];".format(i))

            result = child.solve()
            norm[i]["costs"] = result.objective

        # quality
        with instance.branch() as child:

            child.add_string("obj = quality[{}];".format(i))

            result = child.solve()
            norm[i]["quality"] = result.objective

    return norm

def solve(data, iso, target_active, steps):

    # TODO get rid of that!
    targets = data["item_targets"][:]
    items = range(1,data["k"]+1)

    model = Model("./assign.mzn")
    gecode = Solver.lookup("gecode") # CP solver (does not support float objectives that well)
    cbc = Solver.lookup("cbc") # MIP solver
    instance = Instance(cbc, model)

    # get values of single objectives for normalization purpose
    print("##### start normalizing objectives")
    normalized = normalize(model, cbc, items)
    
    # create objective string
    objective = "constraint obj = "
    for i in items:
        objective += """({cweight}*(costs[{item}]/{cnormalized}) + {qweight}*(quality[{item}]/{qnormalized}))  
                     """.format(cweight = data["target_weights"][i-1], item = i, cnormalized = normalized[i]["costs"], qweight = data["ranking_weights"][i-1], qnormalized = normalized[i]["quality"])
        if i == len(items):
            objective += ";"
        else:
            objective += " + "

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

    index = 0 # index of the currently lowest weighted item target profit margin
    lowest = 0 # currently lowest weighted item target profit margin
    
    c = 0
    count = 0
    status = Status.UNSATISFIABLE
    print("##### start searching for optimal solution")
    while status == Status.UNSATISFIABLE:

        with instance.branch() as child:

            print("####### constraints too hard, need to adjust")

            # TODO THIS WOULD BE GREAT FOR ML!!! was mach ein PM, wenn die Ziele nicht erreicht werden können
            # TODO rausfinden, wie man hier am besten vorgeht, damit man eine Lösung findet! hard-constraints relaxen
            
            if c % steps == 0:
                # find the items with the next lowest weighted target profit margin
                index = get_lowest(data["target_weights"], lowest)
                lowest = data["target_weights"][index]
                # reset item target profit margins
                data["item_targets"] = targets[:]
                c = 0
            
            # TODO get rid of this
            # reduce target profit margin by 1% each time
            data["item_targets"][index] = targets[index] - c/100

            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            child.add_file("./data.json")

            # try to solve the COP with the new target profit margins
            result = child.solve()
            status = result.status
        
        c += 1
        count += 1

    # TODO terminate after x iterations
    # TODO return result as custom object
    print("##### search terminated after {} attempts: {}".format(count, result.status))
    print("#################################################")
    print(result.statistics)
    print("#################################################")
    return(result)
