def get_lowest(targets, lowest):
    l = 100
    index = 0
    for i, value in enumerate(targets):
        if value < l and value > lowest: 
            l = value
            index = i
    return index