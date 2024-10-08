from CPQ_SF_CpqHelper import CPQ_BP_STANDARD_FIELD, CPQ_BP_CUSTOM_FIELD


###############################################################################################
# Class CL_GeneralIntegrationSettings:
#       Class to store feature enablement properties
###############################################################################################
class CL_GeneralIntegrationSettings:
    # Update existing products in Salesforce when sending data from CPQ items
    UPDATE_EXISTING_PRODUCTS_IN_SALESFORCE = False
    # Attach quote to opportunity immediately upon quote is created
    ATTACH_TO_OPP_IMMEDIATELY_ON_QUOTE_CREATED = True
    # Product types that will not be included in CRM opportunity
    PRODUCT_TYPE_EXCLUSION = []
    # Only one quote can be linked to SF opportunity
    ONLY_ONE_QUOTE_LINKED_TO_OPPORTUNITY = False
    # Quote object in CRM is NOT deleted every time action 'Create/Update Opportunity' is executed
    DO_NOT_DELETE_CRM_QUOTE_ON_CREATE_UPDATE = True
    # All revisions from the quote will be attached to the same opportunity
    ALL_REV_ATTACHED_TO_SAME_OPPORTUNITY = True
    # Salesforce Multi-Currency Everywhere
    SF_MCE = False
    # Debugging parameter to log all API calls in CPQ. This should remain inactive.
    LOG_API_CALLS = False
    # Debugging parameter to log all API calls in Custom Table. This should remain inactive.
    LOG_API_CALLS_IN_CUSTOM_TABLE = False
    # Refresh cache for Salesforce object definitions when using tag scripts (CPQ_SF_***_TAG)
    TAG_CACHING = True
    # Update custom object line item and disable deletion of all object line items
    UPDATE_CUSTOM_OBJECT = True
    # Update opportunity line item and disable deletion of all opportunity line items
    UPDATE_OPP_LINE_ITEM = True

###############################################################################################
# Class CL_CpqIntegrationParams:
#       Class to store CPQ key fields involved in the integration
###############################################################################################
class CL_CpqIntegrationParams:

    OPPORTUNITY_ID_FIELD = "CPQ_SF_OPPORTUNITY_ID"
    OPPORTUNITY_NAME_FIELD = "CPQ_SF_OPPORTUNITY_NAME"


###############################################################################################
# Class CL_SalesforceQuoteParams:
#       Class to store key Salesforce Quote key Objects/fields
###############################################################################################
class CL_SalesforceQuoteParams:
    # CRM Quote Object Name
    SF_QUOTE_OBJECT = "Quote__c"
    # CRM Field For Persisting Quote Id
    SF_QUOTE_ID_FIELD = "Quote_ID__c"
    # CRM Field For Persisting Quote Owner Id
    SF_OWNER_ID_FIELD = "Owner_ID__c"
    # CRM Field For Persisting Information About Primary Quote
    SF_PRIMARY_QUOTE_FIELD = "Primary__c"
    # CRM Field For Persisting Information About Quote Currency
    SF_QUOTE_CURRENCY_FIELD = ""
    # Salesforce Opportunity Field on Quote Object
    SF_QUOTE_OPPORTUNITY_FIELD = "Opportunity__c"

    # Salesforce Quote Number field (Should remain set as --> Name)
    SF_QUOTE_NUMBER_FIELD = "Name"
    # Salesforce relationship between Opportunity and Quote
    SF_OPP_QUOTE_REL = "Quotes__r"


###############################################################################################
# Class CL_CrmIdBusinessPartnerMapping:
#       Class to store the look up mapping to identify Accounts & Contacts on Salesforce
###############################################################################################
class CL_CrmIdBusinessPartnerMapping:
    # Default Business partner field used to identify Account/Contact ID on Salesforce
    crmIdMapping = dict()
    crmIdMapping["CpqField"] = "ExternalId"
    # Field Type is either --> CPQ_BP_STANDARD_FIELD/CPQ_BP_CUSTOM_FIELD
    crmIdMapping["CpqFieldType"] = CPQ_BP_STANDARD_FIELD


###############################################################################################
# Class CL_SalesforceAccountObjects:
#       Class to store standard Salesforce Account objects used in Account Mapping
###############################################################################################
class CL_SalesforceAccountObjects:

    SF_OPPORTUNITY_ACC = "OpportunityAccount"
    SF_OPPORTUNITY_PARTNER_ACC_BILL_TO = "OpportunityPartnerRoleAccountBillTo"
    SF_OPPORTUNITY_PARTNER_ACC_SHIP_TO = "OpportunityPartnerRoleAccountShipTo"
    SF_OPPORTUNITY_PARTNER_ACC_END_USER = "OpportunityPartnerRoleAccountEndUser"
    SF_OPPORTUNITY_PARTNER_ROLE_ACC = "OpportunityPartnerRoleAccount"
    SF_OPPORTUNITY_ACC_PARTNER_ROLE_ACC = "OpportunityAccountPartnerRoleAccount"
    SF_OPP_PARTNERS = (SF_OPPORTUNITY_PARTNER_ACC_BILL_TO, SF_OPPORTUNITY_PARTNER_ACC_SHIP_TO,
                       SF_OPPORTUNITY_PARTNER_ACC_END_USER, SF_OPPORTUNITY_PARTNER_ROLE_ACC)


###############################################################################################
# Class CL_SalesforceContactObjects:
#       Class to store standard Salesforce Contact objects used in Contact Mapping
###############################################################################################
class CL_SalesforceContactObjects:

    SF_OPPORTUNITY_ACC_FIRST_CONTACT = "OpportunityAccountFirstContact"
    SF_OPPORTUNIY_ACC_BILL_TO_ROLE = "OpportunityAccountBillToRole"
    SF_OPPORTUNITY_ACC_SHIP_TO_ROLE = "OpportunityAccountShipToRole"
    SF_OPPORTUNIY_ACC_PRIMARY_CONTACT = "OpportunityAccountPrimaryContact"
    SF_OPPORTUNITY_BILL_TO_ROLE = "OpportunityBillToRole"
    SF_OPPORTUNITY_SHIP_TO_ROLE = "OpportunityShipToRole"
    SF_OPPORTUNITY_FIRST_ROLE = "OpportunityFirstRole"
    SF_OPPORTUNITY_PRIMARY_ROLE = "OpportunityPrimaryRole"
    SF_OPPORTUNITY_PARTNER_ACC_FIRST_CONTACT = "OpportunityPartnerAccountFirstContact"
    SF_OPPORTUNITY_PARTNER_ROLE_ACC_PRIMARY_CONTACT = "OpportunityPartnerRoleAccountPrimaryContact"


###############################################################################################
# Class CL_SalesforceIntegrationParams:
#       Class to store key Salesforce Object Identifiers
###############################################################################################
class CL_SalesforceIntegrationParams:
    # Standard Opportunity Objects
    SF_OPPORTUNITY_OBJECT = "Opportunity"
    SF_OPPORTUNITY_LINE_ITEM_OBJECT = "OpportunityLineItem"
    SF_OPPORTUNITY_ID_FIELD = "OpportunityId"
    SF_PRODUCT_OBJECT = "Product2"
    SF_PRICEBOOK_OBJECT = "Pricebook2"
    SF_PRICEBOOK_ENTRY_OBJECT = "PricebookEntry"

    # Standard Objects
    SF_ACCOUNT_OBJECT = "Account"
    SF_CONTACT_OBJECT = "Contact"
    SF_OPPORTUNITY_PARTNER_OBJECT = "OpportunityPartner"
    SF_OPPORTUNITY_CONTACT_OBJECT = "OpportunityContactRole"
    SF_ACCOUNT_CONTACT_ROLE = "AccountContactRole"
    SF_PARTNER = "Partner"
    SF_CONTENT_VERSION = "ContentVersion"
    SF_CONTENT_DOC_LINK = "ContentDocumentLink"
