from geopy.distance import geodesic

def calculate_price_cost(Farm,Slaughthouse,transportCapacity):
    
    mean = Farm.get_avg_weight_kg()
    porks_that_can_be_picked = int(transportCapacity / mean)
    total_weight = porks_that_can_be_picked * mean
    if porks_that_can_be_picked > Farm.get_inventory_pigs():
        porks_that_can_be_picked = Farm.get_inventory_pigs()

    if(mean < Slaughthouse.get_penalty_20_min()):
        return (porks_that_can_be_picked * mean * 0.8 * Farm.get_price_per_kg(),porks_that_can_be_picked,total_weight)
    elif(mean >= Slaughthouse.get_penalty_20_min() and mean < Slaughthouse.get_penalty_15_min()):
        return (porks_that_can_be_picked * mean * 0.85 * Farm.get_price_per_kg(),porks_that_can_be_picked,total_weight)
    elif(mean >= Slaughthouse.get_penalty_15_min() and mean < Slaughthouse.get_penalty_15_max()):
        return (porks_that_can_be_picked * mean * Farm.get_price_per_kg(),porks_that_can_be_picked,total_weight)
    elif(mean >= Slaughthouse.get_penalty_15_max() and mean < Slaughthouse.get_penalty_20_max()):
        return (porks_that_can_be_picked * mean * 0.85 * Farm.get_price_per_kg(),porks_that_can_be_picked,total_weight)
    else:
        return (porks_that_can_be_picked * mean * 0.8 * Farm.get_price_per_kg(),porks_that_can_be_picked,total_weight)
    

def calculate_price_sell(Slaughthouse,weight_picked):
    
    return weight_picked * Slaughthouse.get_price_per_kg()

def calculate_distance(lat1,long1,lat2,long2):
    
    coord1 = (lat1, long1)
    coord2 = (lat2, long2)
    
    return geodesic(coord1, coord2).km


