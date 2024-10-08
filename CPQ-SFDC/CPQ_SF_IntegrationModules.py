from CPQ_SF_Configuration import CL_SalesforceSettings
from CPQ_SF_IntegrationSettings import CL_GeneralIntegrationSettings, CL_SalesforceAccountObjects, CL_SalesforceIntegrationParams, CL_SalesforceQuoteParams
from CPQ_SF_CpqHelper import CL_CpqHelper, CPQ_BILL_TO, CPQ_SHIP_TO, CPQ_END_USER
from CPQ_SF_FunctionModules import get_market_code, get_opportunity_mapping_status, get_customer_crm_account_id, get_quote_market_id, get_quote_opportunity_id
from CPQ_SF_IntegrationReferences import CL_SalesforceApis as API, CL_CompositeRequestReferences as REF, CL_IntegrationReferences as INT_REF
from CPQ_SF_QuoteMapping import quote_integration_mapping
from CPQ_SF_OpportunityMapping import on_opp_create_outbound_opportunity_integration_mapping, on_opp_update_outbound_opportunity_integration_mapping, on_opp_createupdate_outbound_opportunity_integration_mapping
from CPQ_SF_PriceBookMapping import CL_PriceBookMapping
from CPQ_SF_CustomerMapping import CL_OutboundCustomerMapping
from CPQ_SF_ErrorHandler import CL_ErrorHandler
from CPQ_SF_IntegrationMessages import CL_MessageHandler


###############################################################################################
# Class CL_SalesforceIntegrationModules:
#       Class to store integration functions
###############################################################################################
class CL_SalesforceIntegrationModules(CL_CpqHelper):
    class_error_handler = CL_ErrorHandler()
    ###############################################################################################
    # General Function to call Salesforce APIs
    ###############################################################################################
    def call_rest_api(self, url, headers, body, method, integrationReference, permissionList = None):
        response = None
        class_msg_handler = CL_MessageHandler(self.Quote, self.TagParserQuote, None, None)
        # Check permissions
        if permissionList:
            allowed = self.check_api_permissions(permissionList)
            if allowed is False:
                # Set header auth to admin
                adminToken = self.get_admin_auth2_token()
                headers["Authorization"] = "Bearer "+ adminToken
        try:
            if method == API.GET:
                response = RestClient.Get(url, headers)
            elif method == API.POST:
                response = RestClient.Post(url, body, headers)
            elif method == API.PATCH:
                response = RestClient.Patch(url, body, headers)
            elif method == API.DELETE:
                response = RestClient.Delete(url, headers)
        except SystemError as e:
            response = None
            msg = """Integration Error - {integrationReference}: {error}""".format(integrationReference=str(integrationReference), error=str(e))
            if self.Quote:
                class_msg_handler.add_to_quote_msgs(msg)
            # Debugging
            if CL_GeneralIntegrationSettings.LOG_API_CALLS:
                Log.Error("CPQ-SFDC: Integration Error", str(e))
        if response and integrationReference:
            errorMessages = self.class_error_handler.handle_response(response, integrationReference)
            if self.Quote:
                [class_msg_handler.add_to_quote_msgs(msg) for msg in errorMessages if msg]
        # Debugging
        if CL_GeneralIntegrationSettings.LOG_API_CALLS:
            Log.Info("CPQ-SFDC: Request Url ({integrationReference})".format(integrationReference=str(integrationReference)), unicode(url))
            if body:
                Log.Info("CPQ-SFDC: Request Body ({integrationReference})".format(integrationReference=str(integrationReference)), unicode(body))
            if response:
                Log.Info("CPQ-SFDC: Response ({integrationReference})".format(integrationReference=str(integrationReference)), unicode(response))

        # Debugging: Log API calls in custom table --> CPQ_SFDC_API_LOGS
        if CL_GeneralIntegrationSettings.LOG_API_CALLS_IN_CUSTOM_TABLE:
            tableInfo = SqlHelper.GetTable("CPQ_SFDC_API_LOGS")

            def split_string(input_string, chunk_size=4000):
                # Split the input string into chunks of specified size
                return [input_string[i:i + chunk_size] for i in range(0, len(input_string), chunk_size)]

            def add_log(tableInfo, title, content):
                chunks = split_string(unicode(content))

                for chunk in chunks:
                    newrow = {}
                    newrow["DATE"] = DateTime.Now
                    newrow["TITLE"] = title
                    newrow["DESCRIPTION"] = chunk
                    # links logs to both a quote and an opportunity ID
                    if self.Quote:
                        newrow["CARTID"] = self.Quote.QuoteId
                        newrow["CARTCOMPOSITENUMBER"] = self.Quote.CompositeNumber
                        if self.Session["OpportunityId"]:
                            newrow["OPPORTUNITYID"] = self.Session["OpportunityId"]
                        else:
                            newrow["OPPORTUNITYID"] = self.Quote.GetCustomField("CPQ_SF_OPPORTUNITY_ID").Content
                        newrow["OPPORTUNITYNAME"] = self.Quote.GetCustomField("CPQ_SF_OPPORTUNITY_NAME").Content
                    # link the logs to an opportunity Id
                    elif self.Session["OpportunityId"]:
                        newrow["OPPORTUNITYID"] = self.Session["OpportunityId"]
                    tableInfo.AddRow(newrow)
                SqlHelper.Upsert(tableInfo)

            add_log(tableInfo, "CPQ-SFDC: Request Url ({integrationReference})".format(integrationReference=str(integrationReference)), url)

            if body:
                add_log(tableInfo, "CPQ-SFDC: Request Body ({integrationReference})".format(integrationReference=str(integrationReference)), body)

            if response:
                add_log(tableInfo, "CPQ-SFDC: Response ({integrationReference})".format(integrationReference=str(integrationReference)), response)

        return response

    ###############################################################################################
    # Function to construct the Salesforce REST API URL based on the API path and Domain
    ###############################################################################################
    def get_salesforce_api_url(self, apiPath):
        apiUrl = apiPath.format(version=str(CL_SalesforceSettings.SALESFORCE_VERSION))
        url = CL_SalesforceSettings.SALESFORCE_URL + apiUrl
        return url

    ###############################################################################################
    # Function to get Salesforce bearer token (User Session or Admin Sesion)
    ###############################################################################################
    def get_auth2_token(self):
        accessToken = str()
        # Get Admin Token if user session does not exist
        if not self.Session["apiSessionID"]:
            accessToken = self.get_admin_auth2_token()
        # Get User Token if it exist
        else:
            accessToken = self.Session["apiSessionID"]
        return accessToken

    ###############################################################################################
    # Function to get User Session for Salesforce bearer Token
    ###############################################################################################
    def get_user_auth2_token(self):
        accessToken = str()
        if self.Session["apiSessionID"]:
            accessToken = self.Session["apiSessionID"]
        return accessToken

    ###############################################################################################
    # Function to get Admin (Integration User) Salesforce bearer Token
    ###############################################################################################
    def get_admin_auth2_token(self):
        accessToken = str()
        url = CL_SalesforceSettings.SALESFORCE_URL + API.AUTH_API
        # Get Admin access_token
        response = AuthorizedRestClient.GetPasswordGrantOAuthToken(CL_SalesforceSettings.SALESFORCE_PWD, CL_SalesforceSettings.SALESFORCE_SECRET, url, True)
        if response["access_token"] != "" and response["access_token"] is not None:
            accessToken = str(response.access_token)
        else:
            Log.Error("CPQ-SFDC: Integration Authentication Error", str(response))

        return accessToken

    ###############################################################################################
    # Function to set Salesforce REST API header authorization
    ###############################################################################################
    def get_authorization_header(self, bearerToken):
        headers = dict()
        headers["Authorization"] = "Bearer " + bearerToken
        return headers

    ###############################################################################################
    # Function to get the final body of a Composite Request
    ###############################################################################################
    def build_composite_body(self, compositePayload):
        body = dict()
        body["compositeRequest"] = compositePayload
        return body

    ###############################################################################################
    # Function to get the compositeRequest of a singular SObject API call
    ###############################################################################################
    def build_cr_sobject_request(self, url, method, records, referenceId):
        compositeRequest = dict()
        compositeRequest["url"] = url
        compositeRequest["method"] = method
        compositeRequest["referenceId"] = referenceId
        if records:
            compositeRequest["body"] = records
        return compositeRequest

    ###############################################################################################
    # Function to get the compositeRequest of a GET Opportunity request
    ###############################################################################################
    def build_cr_sobject_get_opportunity(self, opportunityId):
        url = API.CR_GET_OPPORTUNITY_API.format(version=str(CL_SalesforceSettings.SALESFORCE_VERSION), opportunityId=str(opportunityId))
        compositeRequest = self.build_cr_sobject_request(url, API.GET, None, CL_SalesforceIntegrationParams.SF_OPPORTUNITY_OBJECT)
        return compositeRequest

    ###############################################################################################
    # Function to add sObject collection payload header (url, method, header) for Composite Requests
    ###############################################################################################
    def get_cr_sobjectcollection_payload_header(self, method, referenceId, records):
        payload = dict()
        if method == API.DELETE:
            payload["url"] = self.build_delete_sobj_collection_url(records)
        else:
            payload["url"] = API.CR_SOBJECT_COLLECTION_API
        payload["method"] = method
        payload["referenceId"] = referenceId
        return payload

    ###############################################################################################
    # Function to build delete SObject collection url
    ###############################################################################################
    def build_delete_sobj_collection_url(self, records):
        url = None
        records = str(records)[1:-1].replace("'", "").replace(" ", "")
        # API path
        url = API.CR_DELETE_SOBJECT_COLLECTION_API.format(version=str(CL_SalesforceSettings.SALESFORCE_VERSION), records=str(records))
        return url

    ###############################################################################################
    # Function to add sObject payload header (url, method, header) for POST Composite Requests
    ###############################################################################################
    def get_sobject_post_payload_header(self, sObject, referenceId):
        payload = dict()
        payload["url"] = API.SOBJECT_API.format(sObject=str(sObject))
        payload["method"] = API.POST
        payload["referenceId"] = referenceId
        return payload

    ###############################################################################################
    # Function to call POST Composite API
    ###############################################################################################
    def post_composite_request(self, bearerToken, compositePayload, integrationReference, permissionList = None):
        # API path
        url = self.get_salesforce_api_url(API.COMPOSITE_API)
        headers = self.get_authorization_header(bearerToken)
        body = self.build_composite_body(compositePayload)
        response = self.call_rest_api(url, headers, body, API.POST, integrationReference, permissionList)

        # check if the response was successful
        if response:
            # convert jobject or jarray to string
            jsonString = RestClient.SerializeToJson(response)
            # user session is invalid --> retry api call with admin session
            if "INVALID_SESSION_ID" in jsonString:
                headers = self.get_authorization_header(self.get_admin_auth2_token())
                response = self.call_rest_api(url, headers, body, API.POST, integrationReference, permissionList)

        return response

    ###############################################################################################
    # Function to call POST SObject Collection API
    ###############################################################################################
    def post_sobjectcollection_request(self, headers, body, integrationReference, permissionList = None):
        # API path
        url = API.SOBJECT_COLLECTION_API
        response = self.call_rest_api(url, headers, body, API.POST, integrationReference, permissionList)

        # check if the response was successful
        if response:
            # convert jobject or jarray to string
            jsonString = RestClient.SerializeToJson(response)
            # user session is invalid --> retry api call with admin session
            if "INVALID_SESSION_ID" in jsonString:
                headers = self.get_authorization_header(self.get_admin_auth2_token())
                response = self.call_rest_api(url, headers, body, API.POST, integrationReference, permissionList)

        return response

    ###############################################################################################
    # Function to call PATCH SObject Collection API
    ###############################################################################################
    def patch_sobjectcollection_request(self, headers, body, integrationReference, permissionList = None):
        # API path
        url = API.SOBJECT_COLLECTION_API
        response = self.call_rest_api(url, headers, body, API.PATCH, integrationReference, permissionList)

        # check if the response was successful
        if response:
            # convert jobject or jarray to string
            jsonString = RestClient.SerializeToJson(response)
            # user session is invalid --> retry api call with admin session
            if "INVALID_SESSION_ID" in jsonString:
                headers = self.get_authorization_header(self.get_admin_auth2_token())
                response = self.call_rest_api(url, headers, body, API.PATCH, integrationReference, permissionList)

        return response

    ###############################################################################################
    # Function to get the compositeRequest to GET Opportunity Partners
    ###############################################################################################
    def build_cr_sobject_get_opportunity_partners(self, opportunityId):
        url = API.CR_GET_OPP_PARTNERS_API.format(opportunityId=str(opportunityId))
        compositeRequest = self.build_cr_sobject_request(url, API.GET, None, REF.GET_OPP_PARTNERS_REFID)
        return compositeRequest

    ###############################################################################################
    # Function to call GET SOQL API
    ###############################################################################################
    def call_soql_api(self, headers, soql, integrationReference=None, permissionList = None):
        # API path
        url = API.GET_SOQL_API.format(sfUrl=str(CL_SalesforceSettings.SALESFORCE_URL), version=str(CL_SalesforceSettings.SALESFORCE_VERSION), soql=str(soql))
        response = self.call_rest_api(url, headers, None, API.GET, integrationReference, permissionList)

        # check if the response was successful
        if response:
            # convert jobject or jarray to string
            jsonString = RestClient.SerializeToJson(response)
            # user session is invalid --> retry api call with admin session
            if "INVALID_SESSION_ID" in jsonString:
                headers = self.get_authorization_header(self.get_admin_auth2_token())
                response = self.call_rest_api(url, headers, None, API.GET, integrationReference, permissionList)

        return response

    ###############################################################################################
    # Function to call GET SOQL API
    ###############################################################################################
    def call_sobject_delete_api(self, bearerToken, url, integrationReference, permissionList = None):
        headers = self.get_authorization_header(bearerToken)
        response = self.call_rest_api(url, headers, None, API.DELETE, integrationReference, permissionList)

        # check if the response was successful
        if response:
            # convert jobject or jarray to string
            jsonString = RestClient.SerializeToJson(response)
            # user session is invalid --> retry api call with admin session
            if "INVALID_SESSION_ID" in jsonString:
                headers = self.get_authorization_header(self.get_admin_auth2_token())
                response = self.call_rest_api(url, headers, None, API.DELETE, integrationReference, permissionList)

        return response

    ###############################################################################################
    # Function to construct payload body for SOQL Composite requests
    ###############################################################################################
    def build_soql_query_composite_payload(self, soql, referenceId):
        # Build payload
        payload = dict()
        payload["url"] = API.CR_SOQL_API.format(version=str(CL_SalesforceSettings.SALESFORCE_VERSION)) + soql
        payload["method"] = API.GET
        payload["referenceId"] = referenceId
        return payload

    ###############################################################################################
    # Function to construct SOQL query to find Quote SObject records
    ###############################################################################################
    def build_quote_soql_query(self):
        soql = """?q=Select+Id+FROM+{sfQuoteObject}+WHERE+{sfQuoteIdField}+=+{quoteId}+AND+{sfOwnerField}+=+{ownerId}"""
        sfQuoteIdField = CL_SalesforceQuoteParams.SF_QUOTE_ID_FIELD
        sfOwnerField = CL_SalesforceQuoteParams.SF_OWNER_ID_FIELD
        soql = soql.format(sfQuoteObject=str(CL_SalesforceQuoteParams.SF_QUOTE_OBJECT), sfQuoteIdField=str(sfQuoteIdField), quoteId=str(self.Quote.QuoteId), sfOwnerField=str(sfOwnerField), ownerId=str(self.Quote.UserId))
        return soql

    ###############################################################################################
    # Function to build SOQL to GET Quote records by the Quote Number
    ###############################################################################################
    def build_soql_get_quote_by_number_record(self, opportunityId):
        condition = """{quoteOpportunityField}='{opportunityId}' and {sfQuoteNameField}='{quoteNumber}'"""
        sfQuoteNameField = CL_SalesforceQuoteParams.SF_QUOTE_NUMBER_FIELD
        condition = condition.format(quoteOpportunityField=CL_SalesforceQuoteParams.SF_QUOTE_OPPORTUNITY_FIELD, opportunityId=str(opportunityId), sfQuoteNameField=str(sfQuoteNameField), quoteNumber=str(self.Quote.CompositeNumber))
        soql = self.build_soql_query(selectedFields="Id",
                                     table=CL_SalesforceQuoteParams.SF_QUOTE_OBJECT,
                                     condition=condition)
        return soql

    ###############################################################################################
    # Function to GET Quote records by the Quote Number
    ###############################################################################################
    def get_quote_by_number(self, bearerToken, opportunityId, integrationReference):
        soql = self.build_soql_get_quote_by_number_record(opportunityId)
        headers = self.get_authorization_header(bearerToken)
        response = self.call_soql_api(headers, soql, integrationReference)
        return response

    ###############################################################################################
    # Function to get Salesforce Quote SObject record (SOQL REST API)
    ###############################################################################################
    def get_sf_quote_record(self, bearerToken):
        response = None
        soql = self.build_quote_soql_query()
        compositePayload = list()
        payload = self.build_soql_query_composite_payload(soql, CL_SalesforceQuoteParams.SF_QUOTE_OBJECT)
        compositePayload.append(payload)
        # Call REST API
        response = self.post_composite_request(bearerToken, compositePayload, INT_REF.REF_GET_SF_QUOTE)
        return response

    ###############################################################################################
    # Function to build Composite Request to GET Quote record
    ###############################################################################################
    def build_cr_get_quote_record(self):
        soql = self.build_quote_soql_query()
        compositeRequest = self.build_soql_query_composite_payload(soql, REF.GET_QUOTE_REFID)
        return compositeRequest

    ###############################################################################################
    # Function to GET Salesforce Quote records that are linked to an opportunity
    ###############################################################################################
    def build_cr_get_opp_quotes(self, opportunityId):
        query = "?q=SELECT+Name,Id,{sfQuoteIdField},{sfOwnerIdField},{sfPrimaryField}+FROM+{sfQuoteObject}+WHERE+{sfQuoteOpportunityField}='{opportunityId}'"
        sfQuoteIdField = CL_SalesforceQuoteParams.SF_QUOTE_ID_FIELD
        sfOwnerIdField = CL_SalesforceQuoteParams.SF_OWNER_ID_FIELD
        sfPrimaryField = CL_SalesforceQuoteParams.SF_PRIMARY_QUOTE_FIELD
        sfQuoteOpportunityField = CL_SalesforceQuoteParams.SF_QUOTE_OPPORTUNITY_FIELD
        query = query.format(sfQuoteIdField=str(sfQuoteIdField),sfOwnerIdField=str(sfOwnerIdField), sfPrimaryField=str(sfPrimaryField), sfQuoteObject=str(CL_SalesforceQuoteParams.SF_QUOTE_OBJECT),sfQuoteOpportunityField=str(sfQuoteOpportunityField),opportunityId=str(opportunityId))
        bearerToken = self.get_auth2_token()
        headers = self.get_authorization_header(bearerToken)
        response = self.call_soql_api(headers, query,INT_REF.REF_GET_QUOTES_LINKED_TO_OPPORTUNITY)
        return response
    ###############################################################################################
    # Function to get key Quote Mappings (CPQ -> Salesforce)
    ###############################################################################################
    def get_key_quote_mappings(self, record):
        # Quote Id
        record[CL_SalesforceQuoteParams.SF_QUOTE_ID_FIELD] = self.Quote.QuoteId
        # User Id
        record[CL_SalesforceQuoteParams.SF_OWNER_ID_FIELD] = self.Quote.UserId
        # Quote Currency
        if CL_SalesforceQuoteParams.SF_QUOTE_CURRENCY_FIELD:
            record[CL_SalesforceQuoteParams.SF_QUOTE_CURRENCY_FIELD] = self.Quote.SelectedMarket.CurrencyCode
        # Quote Number
        record["Name"] = self.Quote.CompositeNumber
        # Mark Quote as Primary
        record[CL_SalesforceQuoteParams.SF_PRIMARY_QUOTE_FIELD] = True
        return record

    ###############################################################################################
    # Function to build Composite Request Record to create Quote
    ###############################################################################################
    def build_cr_record_create_quote(self, opportunityId):
        record = quote_integration_mapping(self.Quote, self.TagParserQuote)
        record = self.get_key_quote_mappings(record)
        # Link to Opportunity
        record[CL_SalesforceQuoteParams.SF_QUOTE_OPPORTUNITY_FIELD] = opportunityId
        record["attributes"] = {"type": CL_SalesforceQuoteParams.SF_QUOTE_OBJECT}
        return record

    ###############################################################################################
    # Function to build Composite Request Record to update Quote
    ###############################################################################################
    def build_cr_record_update_quote(self, sfQuoteId):
        record = quote_integration_mapping(self.Quote, self.TagParserQuote)
        record = self.get_key_quote_mappings(record)
        record["Id"] = sfQuoteId
        record["attributes"] = {"type": CL_SalesforceQuoteParams.SF_QUOTE_OBJECT}
        return record

    ###############################################################################################
    # Function to set Opportunity Main Account in Opportunity Create/Update
    ###############################################################################################
    def get_record_cu_opp_oppaccount(self, record):
        # Opportunity Main Account
        if CL_OutboundCustomerMapping().BILL_TO == CL_SalesforceAccountObjects.SF_OPPORTUNITY_ACC:
            record["AccountId"] = get_customer_crm_account_id(self.Quote, CPQ_BILL_TO)
        elif CL_OutboundCustomerMapping().SHIP_TO == CL_SalesforceAccountObjects.SF_OPPORTUNITY_ACC:
            record["AccountId"] = get_customer_crm_account_id(self.Quote, CPQ_SHIP_TO)
        elif CL_OutboundCustomerMapping().END_CUSTOMER == CL_SalesforceAccountObjects.SF_OPPORTUNITY_ACC:
            record["AccountId"] = get_customer_crm_account_id(self.Quote, CPQ_END_USER)
        return record

    ###############################################################################################
    # Function to build Composite Request Record to create opportunity
    ###############################################################################################
    def build_cr_record_create_opportunity(self):
        record = on_opp_create_outbound_opportunity_integration_mapping(self.Quote, self.TagParserQuote)
        record.update(on_opp_createupdate_outbound_opportunity_integration_mapping(self.Quote, self.TagParserQuote))
        # Status
        oppStatus = get_opportunity_mapping_status(self.Quote)
        if oppStatus:
            record["StageName"] = oppStatus
        # Get Price Book mapping
        sfPriceBook = self.get_sf_pricebook_id()
        # Use Standard Price Book if mapping does not exist
        if sfPriceBook:
            priceBook = sfPriceBook["SF_PRICEBOOK_ID"]
        else:
            priceBook = CL_PriceBookMapping.STANDARD_PRICE_BOOK_ID
        if priceBook: record["Pricebook2Id"] = priceBook
        # Opportunity Currency
        if CL_GeneralIntegrationSettings.SF_MCE:
            currencyCode = self.Quote.SelectedMarket.CurrencyCode
            record["CurrencyIsoCode"] = currencyCode
        # Opportunity Main Account
        record = self.get_record_cu_opp_oppaccount(record)
        record["attributes"] = {"type": CL_SalesforceIntegrationParams.SF_OPPORTUNITY_OBJECT}
        return record

    ###############################################################################################
    # Function to build Composite Request Record to update opportunity
    ###############################################################################################
    def build_cr_record_update_opportunity(self, opportunityId):
        record = on_opp_update_outbound_opportunity_integration_mapping(self.Quote, self.TagParserQuote)
        record.update(on_opp_createupdate_outbound_opportunity_integration_mapping(self.Quote, self.TagParserQuote))
        # Status
        oppStatus = get_opportunity_mapping_status(self.Quote)
        if oppStatus:
            record["StageName"] = oppStatus
        record["Id"] = opportunityId
        # Opportunity Currency
        if CL_GeneralIntegrationSettings.SF_MCE:
            currencyCode = self.Quote.SelectedMarket.CurrencyCode
            record["CurrencyIsoCode"] = currencyCode
        # Opportunity Main Account
        record = self.get_record_cu_opp_oppaccount(record)
        record["attributes"] = {"type": CL_SalesforceIntegrationParams.SF_OPPORTUNITY_OBJECT}
        return record

    ###############################################################################################
    # Function to build Composite Request Record to update PricebookId of the Opportunity ONLY
    ###############################################################################################
    def build_cr_record_update_pricebook(self, opportunityId):
        record = dict()
        record["Id"] = opportunityId
        # Get Price Book mapping
        sfPriceBook = self.get_sf_pricebook_id()
        # Use Standard Price Book if mapping does not exist
        if sfPriceBook:
            priceBook = sfPriceBook["SF_PRICEBOOK_ID"]
        else:
            priceBook = CL_PriceBookMapping.STANDARD_PRICE_BOOK_ID
        if priceBook: record["Pricebook2Id"] = priceBook
        record["attributes"] = {"type": CL_SalesforceIntegrationParams.SF_OPPORTUNITY_OBJECT}
        return record

    ###############################################################################################
    # Function GET singular sObject info
    ###############################################################################################
    def get_sobject(self, bearerToken, sObject, sObjectId):
        url = CL_SalesforceSettings.SALESFORCE_URL + API.GET_SOBJECT_API.format(sObject=str(sObject), sObjectId=str(sObjectId))
        headers = self.get_authorization_header(bearerToken)
        response = self.call_rest_api(url, headers, None, API.GET, INT_REF.REF_GET_SOBJECT_INFO)

        # check if the response was successful
        if response:
            # convert jobject or jarray to string
            jsonString = RestClient.SerializeToJson(response)
            # user session is invalid --> retry api call with admin session
            if "INVALID_SESSION_ID" in jsonString:
                headers = self.get_authorization_header(self.get_admin_auth2_token())
                response = self.call_rest_api(url, headers, None, API.GET, INT_REF.REF_GET_SOBJECT_INFO)

        return response

    ###############################################################################################
    # Function build compositeRequest to remove inactive versions of a Quote from the Opportunity
    ###############################################################################################
    def build_cr_delete_inactive_quotes(self, linkedQuotesResp):
        compositeRequest = None
        # Remove inactive versions of the Quote from the Opportunity
        if linkedQuotesResp:
            quotesToDelete = filter(lambda resp:(resp[CL_SalesforceQuoteParams.SF_QUOTE_ID_FIELD] != self.Quote.QuoteId
                                or resp[CL_SalesforceQuoteParams.SF_OWNER_ID_FIELD] != self.Quote.UserId)
                                and resp["Name"] == self.Quote.CompositeNumber,
                                linkedQuotesResp["body"]["records"])
            if quotesToDelete:
                # Build composite request to remove inactive versions of the Quote from the Opportunity
                records = [str(record["Id"]) for record in quotesToDelete]
                if records:
                    compositeRequest = self.get_cr_sobjectcollection_payload_header(API.DELETE, REF.DEL_INACTIVE_QUOTES_REFID, records)
        return compositeRequest

    ###############################################################################################
    # Function to Post Quote Notes to Chatter
    ###############################################################################################
    def post_notes_into_chatter(self, bearerToken, subjectId, text):
        url = API.POST_CHATTER_API
        body = dict()
        body["feedElementType"] = "FeedItem"
        body["subjectId"] = subjectId

        messageSegments = list()
        messageSeg = dict()
        messageSeg["type"] = "Text"
        messageSeg["text"] = text
        messageSegments.append(messageSeg)
        body["body"] = {"messageSegments" : messageSegments}

        headers = self.get_authorization_header(bearerToken)
        response = self.call_rest_api(url, headers, body, API.POST, INT_REF.REF_POST_QUOTE_NOTES)

        # check if the response was successful
        if response:
            # convert jobject or jarray to string
            jsonString = RestClient.SerializeToJson(response)
            # user session is invalid --> retry api call with admin session
            if "INVALID_SESSION_ID" in jsonString:
                headers = self.get_authorization_header(self.get_admin_auth2_token())
                response = self.call_rest_api(url, headers, body, API.POST, INT_REF.REF_POST_QUOTE_NOTES)

        return response

    ###############################################################################################
    # Function to get Salesforce pricebook id based on mapping
    ###############################################################################################
    def get_sf_pricebook_id(self):
        # Opportunity Price Book
        priceBookMappings = CL_PriceBookMapping().priceBookMapping
        # Get Quote Market System Id
        marketId = get_quote_market_id(self.Quote)
        # Get Price Book mapping
        sfPriceBook = next((mapping for mapping in priceBookMappings if mapping["CPQ_MARKET_ID"] == marketId), None)
        return sfPriceBook

    ###############################################################################################
    # Function to fill look up fields in a record payload (Composite Request)
    ###############################################################################################
    def fill_item_look_up_record(self, item, record):
        # Fill Look Up Fields
        for lookUp in item["lookUps"]:
            record[lookUp["SalesforceField"]] = lookUp["CpqLookUpValue"]
        return record

    ###############################################################################################
    # Function to set market on quote (onQuoteCreate/onQuoteEdit)
    ###############################################################################################
    def set_market_on_quote(self, opportunityResponse):
        priceBookMappings = CL_PriceBookMapping().priceBookMapping
        priceBookMapping = next((mapping for mapping in priceBookMappings if mapping["SF_PRICEBOOK_ID"] == str(opportunityResponse["body"]["Pricebook2Id"])), None)
        if priceBookMapping:
            # Get CPQ Market Code
            marketCode = get_market_code(priceBookMapping["CPQ_MARKET_ID"])
            if marketCode:
                self.Quote.SetMarket(marketCode)

    ###############################################################################################
    # Function to get Describe of all SObjects
    ###############################################################################################
    def get_describe_all(self, bearerToken):
        response = None
        if not self.Session["Describe"]:
            url = API.GET_DESCRIBE_API
            headers = self.get_authorization_header(bearerToken)
            response = self.call_rest_api(url, headers, None, API.GET, INT_REF.REF_GET_DESCRIBE)

            # check if the response was successful
            if response:
                # convert jobject or jarray to string
                jsonString = RestClient.SerializeToJson(response)
                # user session is invalid --> retry api call with admin session
                if "INVALID_SESSION_ID" in jsonString:
                    headers = self.get_authorization_header(self.get_admin_auth2_token())
                    response = self.call_rest_api(url, headers, None, API.GET, INT_REF.REF_GET_DESCRIBE)

            if response:
                self.Session["Describe"] = response
        else:
            response = self.Session["Describe"]
        return response

    ###############################################################################################
    # Function to check Permission
    ###############################################################################################
    def check_api_permissions(self, permissionList):
        # Permission
        allowed = True
        # Stop permission check flag
        checkFinished = False
        # Get Describe
        describe = self.get_describe_all(self.get_auth2_token())
        # Check Permissions
        for permission in permissionList:

            # Get permissions for SObject
            sObjectPermission = next((desc for desc in describe.sobjects if desc["name"]==permission["SObject"]), None)
            if sObjectPermission:
                for action in ["createable", "updateable", "deletable", "queryable"]:
                    if permission[action]:
                        if sObjectPermission[action] == False:
                            allowed = False
                            checkFinished = True
                            break
            # If Object is not present in response then User has no rights for this object
            else:
                allowed = False
                checkFinished = True

            if checkFinished:
                break
        return allowed

    ###############################################################################################
    # Function to build permission check list
    ###############################################################################################
    def build_permission_checklist(self, sObject, createable = False, updateable = False, deletable = False, queryable = False):
        permission = dict()
        permission["SObject"] = sObject
        permission["createable"] = createable
        permission["updateable"] = updateable
        permission["deletable"] = deletable
        permission["queryable"] = queryable
        return permission