from CPQ_SF_Configuration import CL_CPQSettings
from CPQ_SF_IntegrationModules import CL_SalesforceIntegrationModules
from CPQ_SF_IntegrationSettings import CL_SalesforceIntegrationParams, CL_GeneralIntegrationSettings, CL_SalesforceQuoteParams
from CPQ_SF_FunctionModules import set_quote_opportunity_id
from CPQ_SF_CpqHelper import EVENT_CREATE
from CPQ_SF_IntegrationReferences import CL_CompositeRequestReferences as REF, CL_SalesforceApis as API, CL_IntegrationReferences as INT_REF
import CPQ_SF_OpportunityMapping as OpportunityMapping
from CPQ_SF_CustomerModules import CL_CustomerModules
from CPQ_SF_ContactModules import CL_ContactIntegrationModules
from CPQ_SF_CustomObjectModules import CL_CustomObjectModules
from CPQ_SF_IntegrationMessages import CL_MessageHandler, CL_IntegrationMessages


def main(Param, quote):
    editQuoteURl = "/cart/edit?cartcompositenumber={quoteNumber}"
    redirectionUrl = str()
    externalParameters = Param.externalParameters
    # Get Opportunity Id
    opportunityId = externalParameters["opportunityid"].strip()
    if opportunityId:
            class_sf_integration_modules = CL_SalesforceIntegrationModules(None, TagParserQuote, None, Session)
            class_msg_handler = CL_MessageHandler(None, TagParserQuote, None, Session)
            #############################################
            # 1. AUTHORIZATION
            #############################################
            bearerToken = class_sf_integration_modules.get_auth2_token()
            adminToken = class_sf_integration_modules.get_admin_auth2_token()
            # GET other quotes linked to opportunity

            sOQLResponse = class_sf_integration_modules.build_cr_get_opp_quotes(opportunityId)

            # Only one quote can be linked to SF opportunity
            if CL_GeneralIntegrationSettings.ONLY_ONE_QUOTE_LINKED_TO_OPPORTUNITY and CL_GeneralIntegrationSettings.ATTACH_TO_OPP_IMMEDIATELY_ON_QUOTE_CREATED:
                if sOQLResponse:
                    if sOQLResponse["totalSize"] > 0:
                        # Log Error
                        Log.Error("CPQ-SFDC: Create Quote", str(CL_IntegrationMessages.ONLY_ONE_QUOTE_E_MSG))
                        return None, None
            # Create New Quote
            if Param.createQuote:
                quoteNumber = QuoteHelper.CreateNewQuote()
                Quote = QuoteHelper.Edit(quoteNumber)
            # Get current Quote
            else:
                Quote = quote
                quoteNumber = Quote.CompositeNumber
            if Quote:
                # Set redirection URL
                redirectionUrl = CL_CPQSettings.CPQ_URL + editQuoteURl.format(quoteNumber=quoteNumber)
                class_sf_integration_modules = CL_SalesforceIntegrationModules(Quote, TagParserQuote, None, Session)
                class_customer_modules = CL_CustomerModules(Quote, TagParserQuote, None, Session)
                class_contact_modules = CL_ContactIntegrationModules(Quote, TagParserQuote, None, Session)
                class_custom_object_modules = CL_CustomObjectModules(Quote, TagParserQuote, None, Session)
                class_msg_handler = CL_MessageHandler(Quote, TagParserQuote, None, Session)
                ##############################################################
                # 2. COLLECT OPPORTUNITY INFORMATION & CREATE QUOTE & PRIMARY
                ##############################################################
                # Attach Opportunity Id to Quote
                set_quote_opportunity_id(Quote, opportunityId)

                compositePayload = list()
                # Opportunity
                compositeRequest = class_sf_integration_modules.build_cr_sobject_get_opportunity(opportunityId)
                compositePayload.append(compositeRequest)

                # Make Quote Primary - Set other Quotes Primary Flag to False
                if CL_GeneralIntegrationSettings.ATTACH_TO_OPP_IMMEDIATELY_ON_QUOTE_CREATED:
                    if sOQLResponse:
                        if sOQLResponse["totalSize"] > 0:
                            records = list()
                            for linkedQuote in sOQLResponse["records"]:
                                record = dict()
                                record[CL_SalesforceQuoteParams.SF_PRIMARY_QUOTE_FIELD] = False
                                record["Id"] = str(linkedQuote["Id"])
                                record["attributes"] = {"type": CL_SalesforceQuoteParams.SF_QUOTE_OBJECT}
                                records.append(record)
                            if records:
                                compositeRequest = class_sf_integration_modules.get_cr_sobjectcollection_payload_header(API.PATCH, REF.UPDATE_PRIMARY_REFID, None)
                                compositeRequest["body"] = {"records": records}
                                compositePayload.append(compositeRequest)

                # Opportunity Partners
                compositeRequest = class_sf_integration_modules.build_cr_sobject_get_opportunity_partners(opportunityId)
                compositePayload.append(compositeRequest)

                # Attach quote to opportunity immediately upon quote is created
                if CL_GeneralIntegrationSettings.ATTACH_TO_OPP_IMMEDIATELY_ON_QUOTE_CREATED:
                    # Quote
                    records = list()
                    record = class_sf_integration_modules.build_cr_record_create_quote(opportunityId)
                    records.append(record)
                    compositeRequest = class_sf_integration_modules.get_cr_sobjectcollection_payload_header(API.POST, CL_SalesforceQuoteParams.SF_QUOTE_OBJECT, None)
                    compositeRequest["body"] = {"records": records}
                    compositePayload.append(compositeRequest)

                if compositePayload:
                    # Check Create/Update Quote Permissions
                    permissionList = [class_sf_integration_modules.build_permission_checklist(CL_SalesforceQuoteParams.SF_QUOTE_OBJECT, True, True)]
                    # Call API
                    response = class_sf_integration_modules.post_composite_request(bearerToken, compositePayload, INT_REF.REF_UPDATE_OPP_MAKE_PRIMARY, permissionList)

                if response:
                    # Set header fields in Quote
                    # Get Opportunity info
                    opportunityResponse = next((resp for resp in response["compositeResponse"] if str(resp["referenceId"]) == CL_SalesforceIntegrationParams.SF_OPPORTUNITY_OBJECT), None)
                    if opportunityResponse:
                        OpportunityMapping.on_quote_create_inbound_opportunity_integration_mapping(Quote, opportunityResponse["body"])
                        OpportunityMapping.on_quote_createupdate_inbound_opportunity_integration_mapping(Quote, opportunityResponse["body"])

                    # Get Opportunity Partners info
                    opportunityPartnersResp = next((resp for resp in response["compositeResponse"] if str(resp["referenceId"]) == REF.GET_OPP_PARTNERS_REFID), None)

                    if opportunityResponse:
                        # Set Market on quote
                        class_sf_integration_modules.set_market_on_quote(opportunityResponse)
                        ######################################################
                        # 3. COLLECT ADDITIONAL INFORMATION
                        ######################################################
                        response = class_customer_modules.get_customer_details(bearerToken, class_contact_modules, opportunityId, opportunityResponse, opportunityPartnersResp)
                        if response:
                            # Process Customers and Contacts
                            class_customer_modules.process_customers_contacts(response, CustomerHelper, EVENT_CREATE)
                #############################################
                # 4. CUSTOM OBJECTS
                #############################################
                class_custom_object_modules.process_inbound_custom_object_mappings(bearerToken, EVENT_CREATE)
            Quote.Save(False)
            return redirectionUrl, class_msg_handler


# Execute Main and return redirect URL
if Param is not None:
    quote = None
    if "Quote" in globals():
        quote = Quote
    Result, class_msg_handler = main(Param, quote)
    # Display Messages
    if class_msg_handler:
        if class_msg_handler.messages:
            class_msg_handler.show_messages()
