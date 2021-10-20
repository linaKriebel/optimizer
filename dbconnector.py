import logging
import mysql.connector
from mysql.connector import errorcode

import config as cfg

# connect to database
try:
    db = mysql.connector.connect(**cfg.db)
except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
    logging.error("Something is wrong with your user name or password")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
    logging.error("Database does not exist")
  else:
    logging.error(err)

cursor = db.cursor()

def get_project_target(order_id):
    cursor.execute("""
                SELECT a.Zielrendite FROM auftrag a
                WHERE a.AuftragID = %s;""", 
                (order_id, ))
    res = cursor.fetchall()
    return res[0][0] / 100

def is_iso_active(order_id):
    cursor.execute("""
                SELECT a.EN15038Konform_Soll FROM auftrag a
                WHERE a.AuftragID = %s;""", 
                (order_id, ))
    res = cursor.fetchall()
    return True if res[0][0] > 0 else False

def get_items(order_id):
    cursor.execute("""
                SELECT ap.PositionID FROM auftragposition ap
                WHERE ap.IDMain = %s;""", 
                (order_id, ))
    res = cursor.fetchall()
    return [i[0] for i in res]

def get_jobs(order_id):
    cursor.execute("""
                SELECT j.JobID FROM job j
                INNER JOIN auftrag a ON a.AuftragID = j.IDAuftrag 
                WHERE a.AuftragID = %s;""", 
                (order_id, ))
    res = cursor.fetchall()
    return [i[0] for i in res]

def get_jobtype(job_id):
    cursor.execute("""
                SELECT j.Kurzform FROM job j
                WHERE j.JobID = %s;""", 
                (job_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_job_startdate(job_id):
    cursor.execute("""
                SELECT j.TerminVon FROM job j
                WHERE j.JobID = %s;""", 
                (job_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_job_enddate(job_id):
    cursor.execute("""
                SELECT j.TerminBis FROM job j
                WHERE j.JobID = %s;""", 
                (job_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_order_startdate(order_id):
    cursor.execute("""
                SELECT a.AuftragsDatum FROM auftrag a
                WHERE a.AuftragID = %s;""", 
                (order_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_order_enddate(order_id):
    cursor.execute("""
                SELECT a.LieferDatum FROM auftrag a
                WHERE a.AuftragID = %s;""", 
                (order_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_working_hours(resource_id, weekday):
    cursor.execute("""
                SELECT Dauer FROM mitarbeiterwochenplanzeitraum mwpz
                INNER JOIN mitarbeiterwochenplan mwp ON mwpz.WochenplanID = mwp.MitarbeiterWochenplanID
                WHERE mwp.PartnerID = %s AND mwpz.Wochentag = %s""", 
                (resource_id, weekday))
    res = cursor.fetchall()
    return res[0][0] / 2 if res else 0 # 1 Dauer is 0.5 hours -> working hours = Dauer / 2

def get_item_of_job(job_id):
    cursor.execute("""
                SELECT ap.PositionsNr FROM auftragposition ap
                INNER JOIN job j ON j.IDPosition = ap.PositionID
                WHERE j.JobID = %s;""", 
                (job_id, ))
    res = cursor.fetchall()
    return round(res[0][0] / 10)

def get_item_price(item_id):
    cursor.execute("""
                    SELECT SUM(apz.Umfang * apz.PreisProEinheit) FROM auftragposzeilenpreis apz
                    INNER JOIN auftragposition ap ON apz.IDPosition = ap.PositionID
                    WHERE ap.PositionID = %s;""", 
                    (item_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_item_note(item_id):
    cursor.execute("""
                    SELECT Bemerkung FROM auftragposition ap
                    WHERE ap.PositionID = %s;""", 
                    (item_id, ))
    res = cursor.fetchall()
    return res[0][0] if res else None

def get_planned_time(job_id):
    cursor.execute("""
                    SELECT SUM(jp.Umfang * jp.ZeitProEinheitDouble) FROM jobpreis jp
                    WHERE jp.JobID = %s;""", 
                    (job_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_results_of_jobs(order_id):
    cursor.execute("""
                SELECT DISTINCT(rsrr.resource_id) FROM round_search_result_row rsrr
                INNER JOIN round r ON rsrr.round_round_id = r.round_id
                INNER JOIN job j ON r.job_id = j.JobID
                INNER JOIN auftrag a ON j.IDAuftrag = a.AuftragID
                WHERE a.AuftragID = %s AND r.current_round = 1 ORDER BY rsrr.resource_id ASC;""", 
                (order_id, ))
    res = cursor.fetchall()
    return [i[0] for i in res]

def get_resource_name(resource_id, length):

    cursor.execute("""
                SELECT m.Vorname, m.Nachname FROM mitarbeiter m
                WHERE m.MitarbeiterID = %s;""", 
                (resource_id, ))
    res = cursor.fetchall()

    if length == "first":
        return res[0][0]
    if length ==  "last":
        return res[0][1]
    if length ==  "full":
        return res[0][0] + " " + res[0][1]
    else:
        print("Error")

def get_successors(job_id):
    cursor.execute("""
                SELECT jna.NextJobketteItemID FROM jobkettenachfolger_auftrag jna
                WHERE jna.JobketteItemID = %s;""", 
                (job_id, ))
    res = cursor.fetchall()
    return [r[0] for r in res]

def is_result(job_id, resource_id):
    cursor.execute("""
                SELECT EXISTS(SELECT rsrr.round_search_result_row_id FROM round_search_result_row rsrr 
                INNER JOIN round r ON rsrr.round_round_id = r.round_id
                INNER JOIN job j ON r.job_id = j.JobID
                WHERE j.JobID = %s AND rsrr.resource_id = %s AND r.current_round = 1);""", 
                (job_id, resource_id))
    res = cursor.fetchall()
    return res[0][0]

def get_result_row(job_id, resource_id):
    cursor.execute("""
                SELECT rsrr.round_search_result_row_id FROM round_search_result_row rsrr 
                INNER JOIN round r ON rsrr.round_round_id = r.round_id
                INNER JOIN job j ON r.job_id = j.JobID
                WHERE j.JobID = %s AND rsrr.resource_id = %s AND r.current_round = 1;""", 
                (job_id, resource_id))
    res = cursor.fetchall()
    return res[0][0]

def get_current_round(job_id):
    cursor.execute("""
                SELECT r.round_id FROM round r
                INNER JOIN job j ON r.job_id = j.JobID
                WHERE j.JobID = %s AND r.current_round = 1;""", 
                (job_id, ))
    res = cursor.fetchall()
    return res[0][0]

def get_rank(job_id, resource_id):
    cursor.execute("""
                SELECT rsrr.rank FROM round_search_result_row rsrr 
                INNER JOIN round r ON rsrr.round_round_id = r.round_id
                INNER JOIN job j ON r.job_id = j.JobID
                WHERE j.JobID = %s AND rsrr.resource_id = %s AND r.current_round = 1;""", 
                (job_id, resource_id))
    res = cursor.fetchall()
    return res[0][0]

def get_busy(job_id, resource_id):
    cursor.execute("""
                SELECT rsrr.busy FROM round_search_result_row rsrr 
                INNER JOIN round r ON rsrr.round_round_id = r.round_id
                INNER JOIN job j ON r.job_id = j.JobID
                WHERE j.JobID = %s AND rsrr.resource_id = %s AND r.current_round = 1;""", 
                (job_id, resource_id))
    res = cursor.fetchall()
    return res[0][0]

# deprecated
# def get_price(row_id):
#     cursor.execute("""
#                 SELECT rsrrrm.ranking_value from round_search_result_row_ranking_mapping rsrrrm 
#                 INNER JOIN round_search_result_row rsrr ON rsrr.round_search_result_row_id = rsrrrm.round_search_result_row_id
#                 WHERE rsrr.round_search_result_row_id = %s AND rsrrrm.ranking_method = 'price';""", 
#                 (row_id, ))
#     res = cursor.fetchall()
#     return res[0][0] if res else 0

def get_price(row_id):
    cursor.execute("""
                SELECT rsrrrr.price_value from round_search_result_row_ranking rsrrrr 
                WHERE rsrrrr.round_search_result_row_round_search_result_row_id = %s;""", 
                (row_id, ))
    res = cursor.fetchall()
    return res[0][0] if res else 0

def get_price_currency(row_id):
    cursor.execute("""
                SELECT rsrrrm.price_unit from round_search_result_row_ranking rsrrrr 
                WHERE rsrrrr.round_search_result_row_round_search_result_row_id = %s;""", 
                (row_id, ))
    res = cursor.fetchall()
    return res[0][0] if res else None    

def is_target_profit_margin_active():
    cursor.execute("""
                SELECT ses.boolean_value from system_einstellung_system ses 
                WHERE ses.system_einstellung_key = 'VerhindereUnterschreitenZielrendite';""", 
                ())
    res = cursor.fetchall()
    return True if res[0][0] > 0 else False