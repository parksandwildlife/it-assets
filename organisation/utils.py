from data_storage import AzureBlobStorage
from dbca_utils.utils import env
import json
import os
import re


def get_azure_users_json(container, azure_json_path):
    """Pass in the container name and path to a JSON dump of Azure AD users, return parsed JSON.
    """
    connect_string = env('AZURE_CONNECTION_STRING', '')
    if not connect_string:
        return None
    store = AzureBlobStorage(connect_string, container)
    return json.loads(store.get_content(azure_json_path))


def find_user_in_list(user_list, email=None, objectid=None):
    """For a list of dicts (Azure/onprem AD users), find the first one matching email/objectid (or None).
    """
    if email:
        for user in user_list:
            if 'Mail' in user and user['Mail'] and user['Mail'].lower() == email.lower():  # Azure AD
                return user
            elif 'EmailAddress' in user and user['EmailAddress'] and user['EmailAddress'].lower() == email.lower():  # Onprem AD
                return user
    if objectid:
        for user in user_list:
            if 'ObjectId' in user and user['ObjectId'] and user['ObjectId'] == objectid:  # Azure AD
                return user
            elif 'ObjectGUID' in user and user['ObjectGUID'] and user['ObjectGUID'] == objectid:  # Onprem AD
                return user
    return None


def update_deptuser_from_onprem_ad(ad_user, dept_user):
    """For given onprem AD user and DepartmentUser objects, update the DepartmentUser object fields
    with values from AD (the source of truth for these values).
    Currently, only ObjectGUID and SamAccountName should be synced from on-prem AD.
    """
    dept_user.ad_guid = ad_user['ObjectGUID']
    dept_user.username = ad_user['SamAccountName']
    dept_user.save()


def update_deptuser_from_azure(azure_user, dept_user):
    """For given Azure AD user and DepartmentUser objects, update the DepartmentUser object fields
    with values from Azure (the source of truth for these values).
    """
    if azure_user['ObjectId'] != dept_user.azure_guid:
        dept_user.azure_guid = azure_user['ObjectId']
    if azure_user['AccountEnabled'] != dept_user.active:
        dept_user.active = azure_user['AccountEnabled']
    if azure_user['Mail'] != dept_user.email:
        dept_user.email = azure_user['Mail']
    if azure_user['DisplayName'] != dept_user.name:
        dept_user.name = azure_user['DisplayName']
    if azure_user['GivenName'] != dept_user.given_name:
        dept_user.given_name = azure_user['GivenName']
    if azure_user['Surname'] != dept_user.surname:
        dept_user.surname = azure_user['Surname']
    if azure_user['MailNickName'] != dept_user.mail_nickname:
        dept_user.mail_nickname = azure_user['MailNickName']
    if azure_user['DirSyncEnabled'] != dept_user.dir_sync_enabled:
        dept_user.dir_sync_enabled = azure_user['DirSyncEnabled']

    dept_user.proxy_addresses = [i.lower().replace('smtp:', '') for i in azure_user['ProxyAddresses'] if i.lower().startswith('smtp')]

    licence_pattern = 'SkuId:\s[a-z0-9-]+'
    skus = [re.search(licence_pattern, i)[0].replace('SkuId: ', '') for i in azure_user['AssignedLicenses'] if re.search(licence_pattern, i)]
    dept_user.assigned_licences = []
    # MS licence SKU reference:
    # https://docs.microsoft.com/en-us/azure/active-directory/users-groups-roles/licensing-service-plan-reference
    ms_licence_skus = {
        'c5928f49-12ba-48f7-ada3-0d743a3601d5': 'VISIO Online Plan 2',  # VISIOCLIENT
        '1f2f344a-700d-42c9-9427-5cea1d5d7ba6': 'STREAM',
        'b05e124f-c7cc-45a0-a6aa-8cf78c946968': 'ENTERPRISE MOBILITY + SECURITY E5',  # EMSPREMIUM
        'c7df2760-2c81-4ef7-b578-5b5392b571df': 'OFFICE 365 E5',  # ENTERPRISEPREMIUM
        '87bbbc60-4754-4998-8c88-227dca264858': 'POWERAPPS_INDIVIDUAL_USER',
        '6470687e-a428-4b7a-bef2-8a291ad947c9': 'WINDOWS_STORE',
        '6fd2c87f-b296-42f0-b197-1e91e994b900': 'OFFICE 365 E3',  # ENTERPRISEPACK
        'f30db892-07e9-47e9-837c-80727f46fd3d': 'FLOW_FREE',
        '440eaaa8-b3e0-484b-a8be-62870b9ba70a': 'PHONESYSTEM_VIRTUALUSER',
        'bc946dac-7877-4271-b2f7-99d2db13cd2c': 'FORMS_PRO',
        'dcb1a3ae-b33f-4487-846a-a640262fadf4': 'POWERAPPS_VIRAL',
        '338148b6-1b11-4102-afb9-f92b6cdc0f8d': 'DYN365_ENTERPRISE_P1_IW',
        '6070a4c8-34c6-4937-8dfb-39bbc6397a60': 'MEETING_ROOM',
        'a403ebcc-fae0-4ca2-8c8c-7a907fd6c235': 'POWER_BI_STANDARD',
        '111046dd-295b-4d6d-9724-d52ac90bd1f2': 'Microsoft Defender Advanced Threat Protection',  # WIN_DEF_ATP
        '710779e8-3d4a-4c88-adb9-386c958d1fdf': 'TEAMS_EXPLORATORY',
        'efccb6f7-5641-4e0e-bd10-b4976e1bf68e': 'ENTERPRISE MOBILITY + SECURITY E3',  # EMS
        '90d8b3f8-712e-4f7b-aa1e-62e7ae6cbe96': 'SMB_APPS',
        'fcecd1f9-a91e-488d-a918-a96cdb6ce2b0': 'AX7_USER_TRIAL',
        '093e8d14-a334-43d9-93e3-30589a8b47d0': 'RMSBASIC',
        '53818b1b-4a27-454b-8896-0dba576410e6': 'PROJECT ONLINE PROFESSIONAL',  # PROJECTPROFESSIONAL
        '18181a46-0d4e-45cd-891e-60aabd171b4e': 'OFFICE 365 E1',  # STANDARDPACK
        '06ebc4ee-1bb5-47dd-8120-11324bc54e06': 'MICROSOFT 365 E5',
    }
    for sku in skus:
        if sku in ms_licence_skus:
            dept_user.assigned_licences.append(ms_licence_skus[sku])
        else:
            dept_user.assigned_licences.append(sku)

    dept_user.save()


def deptuser_azure_sync(dept_user, container='azuread', azure_json='aadusers.json'):
    """Utility function to perform all of the steps to sync up a single DepartmentUser and Azure AD.
    Function may be run as-is, or queued as an asynchronous task.
    """
    azure_users = get_azure_users_json(container, azure_json)
    azure_user = find_user_in_list(azure_users, objectid=dept_user.azure_guid)

    if azure_user:
        update_deptuser_from_azure(azure_user, dept_user)
        dept_user.generate_ad_actions(azure_user)
        dept_user.audit_ad_actions(azure_user)


def get_photo_path(instance, filename='photo.jpg'):
    """NOTE: unused, but retain for historical migration purposes.
    """
    return os.path.join('user_photo', '{0}.{1}'.format(instance.id, os.path.splitext(filename)))


def get_photo_ad_path(instance, filename='photo.jpg'):
    """NOTE: unused, but retain for historical migration purposes.
    """
    return os.path.join('user_photo_ad', '{0}.{1}'.format(instance.id, os.path.splitext(filename)))
