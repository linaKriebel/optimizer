import logging

from zeep import Client
from zeep.xsd.types.builtins import Boolean

import config as cfg

hostname = None
uuid = None
TYPE = 3 # 3 = order, 1 = quote

def login(host):
    global hostname
    global uuid

    hostname = host

    client = Client('https://{}/PlunetAPI?wsdl'.format(hostname))
    uuid = client.service.login(cfg.bm['user'], cfg.bm['password'])
    return uuid

###### ORDER #####

def get_order(order):
    client = Client('https://{}/DataOrder30?wsdl'.format(hostname))
    result = client.service.getOrderObject2(uuid, order)
    if result.statusMessage == 'OK':
        return result.data
    else:
        logging.ERROR("No order found with given number.")

def get_order_id(order):
    client = Client('https://{}/DataOrder30?wsdl'.format(hostname))
    result = client.service.getOrderID(uuid, order)
    if result.statusMessage == 'OK':
        return result.data.getData()
    else:
        logging.ERROR("No order found with given number.")

def iso_active(order_id):
    client = Client('https://{}/DataOrder30?wsdl'.format(hostname))
    result = client.service.checkEN15038(uuid, order_id)
    if result.statusMessage == 'OK':
        result.data.getData()
    else:
        return result.statusMessage

def set_description(order_id, description):
    client = Client('https://{}/DataOrder30?wsdl'.format(hostname))
    result = client.service.setSubject(uuid, description, order_id)
    if result.statusMessage == 'OK':
        logging.info(f"Statistics successfully updated for order {order_id}.")
    else:
        logging.warning(f"A problem occurred while updating statistics for order {order_id}: {result.statusMessage}")

##### ITEM #####

def get_items(order_id):
    client = Client('https://{}/DataItem30?wsdl'.format(hostname))
    result = client.service.getAllItems(uuid, order_id, TYPE)
    if result.statusMessage == 'OK':
        return result.data
    else:
        logging.ERROR("No order found with given number.")

def get_jobs_of_item(item_id):
    client = Client('https://{}/DataItem30?wsdl'.format(hostname))
    result = client.service.getJobs(uuid, TYPE, item_id)
    if result.statusMessage == 'OK':
        return result.data
    else:
        logging.ERROR("No item found with given number.")

def get_price(item_id):
    client = Client('https://{}/DataItem30?wsdl'.format(hostname))
    result = client.service.getTotalPrice(uuid, TYPE, item_id)
    if result.statusMessage == 'OK':
        return result.data
    else:
        logging.ERROR("No item found with given number.")

def get_note(item_id):
    client = Client('https://{}/DataItem30?wsdl'.format(hostname))
    result = client.service.getComment(uuid, TYPE, item_id)
    if result.statusMessage == 'OK':
        return result.data
    else:
        logging.error(f"No item found with given number {item_id}: {result.statusMessage}")

def set_note(item_id, note):
    client = Client('https://{}/DataItem30?wsdl'.format(hostname))
    result = client.service.setComment(uuid, note, TYPE, item_id) 
    if result.statusMessage == 'OK':
        logging.info(f"Statistics successfully updated for item {item_id}.")
    else:
        logging.warning(f"A problem occurred while updating statistics for item {item_id}: {result.statusMessage}")

##### JOB #####

##### ROUND #####

def get_round(round_id):
    client = Client('https://{}/DataJobRound30?wsdl'.format(hostname))
    round = client.service.getRoundObject(uuid, round_id).data
    return round

def get_current(job_id):
    client  = Client('https://{}/DataJobRound30?wsdl'.format(hostname))
    round_ids = client.service.getAllRoundIDs(uuid, job_id, TYPE)
    
    # TODO find the real current round, this is just a workaround
    for round_id in round_ids:
        round = client.service.getRoundObject(uuid, round_id).data
        if round.jobRoundNumber == 1:
            return round_id
        else:
            return None

def get_resources(round_id):
    client  = Client('https://{}/DataJobRound30?wsdl'.format(hostname))
    result = client.service.getResourcesForRound(uuid, round_id)
    return result

def set_resource(resource_id, round_id):
    client  = Client('https://{}/DataJobRound30?wsdl'.format(hostname))
    result = client.service.setResourceForReview(uuid, resource_id, 0, round_id)
    if result.statusMessage == 'OK':
        logging.info(f"Resource {resource_id} successfully set in round {round_id}.")
    else:
        logging.warning((f"A problem occurred while setting resource {resource_id} in round {round_id}: {result.statusMessage}"))
