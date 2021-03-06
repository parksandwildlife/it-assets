import simdjson
import traceback
import logging
import datetime
import re

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from data_storage import HistoryDataConsumeClient,LocalStorage,exceptions
from .models import Cluster,Workload,Container,ContainerLog,clean_containerlogs
from itassets.utils import LogRecordIterator

from .utils import to_datetime,set_fields
from .containerstatus_harvester import get_containerstatus_client
from .podstatus_harvester import get_podstatus_client

logger = logging.getLogger(__name__)

log_levels = [
    (re.compile("(^|[^a-zA-Z]+)TRACE[^a-zA-Z]+"),(ContainerLog.TRACE,True)),
    (re.compile("(^|[^a-zA-Z]+)DEBUG[^a-zA-Z]+"),(ContainerLog.DEBUG,True)),
    (re.compile("(^|[^a-zA-Z]+)INFO[^a-zA-Z]+"),(ContainerLog.INFO,True)),
    (re.compile("(^|[^a-zA-Z]+)WARN(ING)?[^a-zA-Z]+"),(ContainerLog.WARNING,True)),
    (re.compile("(^|[^a-zA-Z]+)ERROR[^a-zA-Z]+"),(ContainerLog.ERROR,True)),
    (re.compile("(^|\s+)(level|lvl)\s*=\s*trace\s+",re.IGNORECASE),(ContainerLog.TRACE,True)),
    (re.compile("(^|\s+)(level|lvl)\s*=\s*debug\s+",re.IGNORECASE),(ContainerLog.DEBUG,True)),
    (re.compile("(^|\s+)(level|lvl)\s*=\s*info\s+",re.IGNORECASE),(ContainerLog.INFO,True)),
    (re.compile("(^|\s+)(level|lvl)\s*=\s*warn(ing)?\s+",re.IGNORECASE),(ContainerLog.WARNING,True)),
    (re.compile("(^|\s+)(level|lvl)\s*=\s*error\s+",re.IGNORECASE),(ContainerLog.ERROR,True)),
    (re.compile("(exception|error|failed|wrong|err|traceback)\s+",re.IGNORECASE),(ContainerLog.ERROR,False))
]
_containerlog_client = None
def get_containerlog_client():
    """
    Return the blob resource client
    """
    global _containerlog_client
    if _containerlog_client is None:
        _containerlog_client = HistoryDataConsumeClient(
            LocalStorage(settings.CONTAINERLOG_REPOSITORY_DIR),
            settings.CONTAINERLOG_RESOURCE_NAME,
            settings.RESOURCE_CLIENTID,
            max_saved_consumed_resources=settings.CONTAINERLOG_MAX_SAVED_CONSUMED_RESOURCES
        )
    return _containerlog_client

def update_latest_containers(context,containerlog):
    container = containerlog.container
    workload_key = (container.workload.cluster.id,container.workload.namespace.name,container.workload.name,container.workload.kind)
    if workload_key not in context["workloads"]:
        workload_update_fields = []
        workload = container.workload
        context["workloads"][workload_key] = (workload,workload_update_fields)
    else:
        workload,workload_update_fields = context["workloads"][workload_key]

    if not workload.latest_containers:
        return

    if containerlog.level == ContainerLog.WARNING:
        status = Workload.WARNING | Workload.INFO
    elif containerlog.level == ContainerLog.ERROR:
        status = Workload.ERROR | Workload.INFO
    else:
        status = Workload.INFO

    if "latest_containers" not in workload_update_fields:
        index = 0
        while index < len(workload.latest_containers):
            container_data = workload.latest_containers[index]
            if container_data[0] != container.id:
                index += 1
                continue
            else:
                if container_data[2] & status != status:
                    workload.new_latest_containers = [list(o) for o in workload.latest_containers]
                    workload.new_latest_containers[index][2] = workload.latest_containers[index][2] | status
                    workload_update_fields.append("latest_containers")
                break
    else:
        for container_data in workload.new_latest_containers:
            if container_data[0] != container.id:
                continue
            else:
                container_data[2] = container_data[2] | status
                break

def process_status_file(context,metadata,status_file):
    if settings.CONTAINERLOG_STREAMING_PARSE:
        status_records = LogRecordIterator(status_file)
    else:
        with open(status_file,"r") as f:
            status_records = simdjson.loads(f.read())

    records = 0
    for record in status_records:
        try:
            if any(not (record.get(key) or "").strip() for key in ("computer","containerid","logentry","logtime")):
                #data is incomplete,ignore
                continue

            logtime = to_datetime(record["logtime"])
            containerid = record["containerid"].strip()
            message = record["logentry"].strip()
            if not message:
                continue
            message = message.replace("\\n","\n")
            source = (record["logentrysource"] or "").strip() or None
            level = None
            newmessage = False
            for log_level_re,value in log_levels:
                if log_level_re.search(message):
                    level,newmessage = value
                    break

            if level is None:
                if source.lower() in ('stderr',):
                    level = ContainerLog.ERROR
                else:
                    level = ContainerLog.INFO

            computer = record["computer"].strip()
            cluster = None
            clustername = None

            if computer in context["clusters"]:
                cluster = context["clusters"][computer]
            elif record.get("resourceid"):
                resourceid = record["resourceid"].strip().rsplit("/",1)[-1]
                if resourceid in context["clusters"]:
                    cluster = context["clusters"][resourceid]
                else:
                    clustername = resourceid
            else:
                clustername = computer

            if not cluster:
                try:
                    cluster = Cluster.objects.get(name=clustername)
                except ObjectDoesNotExist as ex:
                    cluster = Cluster(name=clustername,added_by_log=True)
                    cluster.save()

                context["clusters"][clustername] = cluster
            """
            if cluster.name != 'az-k3s-oim01':
                continue
            """

            key = (cluster.id,containerid)
            if key in context["containers"]:
                container,container_update_fields = context["containers"][key]
            else:
                try:
                    container = Container.objects.get(cluster=cluster,containerid=containerid)
                except ObjectDoesNotExist as ex:
                    if settings.CONTAINERLOG_FAILED_IF_CONTAINER_NOT_FOUND:
                        raise Exception("ContainerId({}) in log resource({}) Not Found".format(containerid,metadata))
                    else:
                        continue
                container_update_fields = []
                context["containers"][key] = (container,container_update_fields)

            key = (cluster.id,containerid)
            if key in context["containerlogs"]:
                containerlog = context["containerlogs"][key]
                containerlog.archiveid = metadata["resource_id"]
            else:
                containerlog = ContainerLog(archiveid=metadata["resource_id"])
                context["containerlogs"][key] = containerlog

            if not containerlog.logtime:
                containerlog.id = None
                containerlog.container = container
                containerlog.logtime = logtime
                containerlog.latest_logtime = logtime
                containerlog.source = source
                #containerlog.message = "{}:{}".format(logtime.strftime("%Y-%m-%d %H:%M:%S.%f"),message)
                containerlog.message = message
                containerlog.level = level
            elif newmessage or logtime >= (containerlog.latest_logtime + datetime.timedelta(seconds=1)) or containerlog.source != source :
                records += 1

                containerlog.save()
                update_latest_containers(context,containerlog)
                container_update_fields = set_fields(container,[
                    ("log", True),
                    ("warning", True if containerlog.level == ContainerLog.WARNING else container.warning),
                    ("error", True if containerlog.level == ContainerLog.ERROR else container.error),
                ],container_update_fields)
                if newmessage and containerlog.logtime >= logtime:
                    #more than one logs at the same time, add one millesconds to the logtime because of unique index
                    logtime = containerlog.logtime + datetime.timedelta(milliseconds=1)
                containerlog.id = None
                containerlog.container = container
                containerlog.logtime = logtime
                containerlog.latest_logtime = logtime
                containerlog.source = source
                #containerlog.message = "{}:{}".format(logtime.strftime("%Y-%m-%d %H:%M:%S.%f"),message)
                containerlog.message = message
                containerlog.level = level
            else:
                if level > containerlog.level:
                    containerlog.level = level
                #containerlog.message = "{}\n{}:{}".format(containerlog.message,logtime.strftime("%Y-%m-%d %H:%M:%S.%f"),message)
                containerlog.message = "{}\n{}".format(containerlog.message,message)
                if logtime > containerlog.latest_logtime:
                    containerlog.latest_logtime = logtime
        except Exception as ex:
            #delete already added records from this log file
            logger.error("Failed to parse pod status record({}).{}".format(record,traceback.format_exc()))
            raise Exception("Failed to parse pod status record({}).{}".format(record,str(ex)))

    #save the last message
    containerlogs = [o for o in context["containerlogs"].values() if o.logtime and o.container]
    containerlogs.sort(key=lambda o:o.logtime)
    for containerlog in containerlogs:
        records += 1
        containerlog.save()
        container = containerlog.container
        update_latest_containers(context,containerlog)
        key = (container.cluster.id,container.containerid)
        if key in context["containers"]:
            container,container_update_fields = context["containers"][key]
        else:
            container_update_fields = []
            context["containers"][key] = (container,container_update_fields)
        container_update_fields = set_fields(container,[
            ("log", True),
            ("warning", True if containerlog.level == ContainerLog.WARNING else container.warning),
            ("error", True if containerlog.level == ContainerLog.ERROR else container.error),
        ],container_update_fields)
        containerlog.id = None
        containerlog.logtime = None
        containerlog.level = None
        containerlog.message = None
        containerlog.source = None
        containerlog.container = None
        containerlog.latest_logtime = None

    #save terminated containers
    terminated_keys = []
    for key,value  in context["containers"].items():
        container,container_update_fields = value
        if container.container_terminated and (container.container_terminated + datetime.timedelta(minutes=30)) < metadata["archive_endtime"]:
            terminated_keys.append(key)
            if not container.pk:
                container.save()
            elif container_update_fields:
                container.save(update_fields=container_update_fields)

    #delete terminated containers from cache
    for key in terminated_keys:
        del context["containers"][key]
        if key in context["containerlogs"]:
            del context["containerlogs"][key]
    logger.info("Harvest {1} records from file '{0}'".format(status_file,records))

def process_status(context):
    def _func(status,metadata,status_file):
        if status != HistoryDataConsumeClient.NEW:
            raise Exception("The status of the consumed history data shoule be New, but currently consumed histroy data's status is {},metadata={}".format(
                get_containerlog_client().get_consume_status_name(status),
                metadata
            ))
            for name,key,client in (("podstatus","podstatus_client",get_podstatus_client(cache=False)),("containerstatus","containerstatus_client",get_containerstatus_client(cache=False))):
                if key in context["clients"]:
                    last_consume = context["clients"][key]
                    if last_consume[1]["archive_endtime"] >= metadata["archive_endtime"]:
                        continue
                last_consume = client.last_consume
                if not last_consume:
                    raise exceptions.StopConsuming("Can't consume containerlog file({0}) which archive_endtimne is {1}, because no {2} file was consumed.".format(
                        metadata["resource_id"],
                        metadata["archive_endtime"],
                        name
                    ))
                elif last_consume[1]["archive_endtime"] < metadata["archive_endtime"]:
                    raise exceptions.StopConsuming("Can't consume containerlog file({0}) which archive_endtimne({1}) is after the archive_endtime({4}) of the last consumed {2} file({3}) that was consumed at {5}".format(
                        metadata["resource_id"],
                        metadata["archive_endtime"],
                        name,
                        last_consume[1]["resource_id"],
                        last_consume[1]["archive_endtime"],
                        last_consume[2]["consume_date"],
                    ))
                context["clients"][key] = last_consume

        ContainerLog.objects.filter(archiveid=metadata["resource_id"]).delete()

        process_status_file(context,metadata,status_file)

        for container,container_update_fields  in context["containers"].values():
            if not container.pk:
                container.save()
            elif container_update_fields:
                container.save(update_fields=container_update_fields)
                container_update_fields.clear()

        #save workload
        for workload,workload_update_fields in context["workloads"].values():
            if not workload.id:
                workload.save()
            elif workload_update_fields:
                if Workload.objects.filter(id=workload.id,latest_containers=workload.latest_containers).update(latest_containers=workload.new_latest_containers) == 0:
                    #workload's latest_containers changed
                    db_workload = Workload.objects.filter(id=workload.id).first()
                    if not db_workload or not db_workload.latest_containers:
                        continue
                    changed = False
                    for container in db_workload.latest_containers:
                        for o in workload.new_latest_containers:
                            if container[0] == o[0]:
                                container[2] = o[2]
                                changed = True
                                break
                    if changed:
                        db_workload.save(update_fields=workload_update_fields)
                        workload.latest_containers = db_workload.latest_containers
                else:
                    workload.latest_containers = workload.new_latest_containers
                workload_update_fields.clear()
                delattr(workload,"new_latest_containers")

        context["renew_lock_time"] = context["f_renew_lock"](context["renew_lock_time"])

    return _func

def harvest(reconsume=False):
    try:
        renew_lock_time = get_containerlog_client().acquire_lock(expired=settings.CONTAINERLOG_MAX_CONSUME_TIME_PER_LOG)
    except exceptions.AlreadyLocked as ex:
        msg = "The previous harvest process is still running.{}".format(str(ex))
        logger.info(msg)
        return ([],[(None,None,None,msg)])

    try:
        if reconsume:
            if get_containerlog_client().is_client_exist(clientid=settings.RESOURCE_CLIENTID):
                get_containerlog_client().delete_clients(clientid=settings.RESOURCE_CLIENTID)
            clean_containerlogs()


        context = {
            "reconsume":reconsume,
            "renew_lock_time":renew_lock_time,
            "f_renew_lock":get_containerlog_client().renew_lock,
            "clients":{},
            "clusters":{},
            "namespaces":{},
            "workloads":{},
            "containers":{},
            "containerlogs":{},
            "terminated_containers":set()
        }
        #consume nginx config file
        result = get_containerlog_client().consume(process_status(context))

        return result

    finally:
        get_containerlog_client().release_lock()



