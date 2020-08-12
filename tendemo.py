# tencent cloud api demo
# Reference:
# https://cloud.tencent.com/document/product/1093/37823
# https://cloud.tencent.com/document/api/1093/35640
# https://cloud.tencent.com/document/api/1093/35641

import json
import time

size5m = 5*1024*1024
lang_supported = ["zh", "en", "ca", "ja"]
model_supported = ["8k", "16k"]

api_host = "asr.tencentcloudapi.com"
api_url = "/"
request_method = "GET"

up_api_action = "CreateRecTask"
up_api_version = "2019-06-14"

res_api_action = "DescribeTaskStatus"
res_api_version = "2019-06-14"

service_name = "asr"
end_mark = "tc3_request"

file_url_raw = ""
sign_algo_name = "TC3-HMAC-SHA256"

# logger
def stg_log(msg = "test log", level="info", filenanme = "./tendemo.log", do_print = 1):
    """
    msg: info message to be printed
    level: info or warning or error
    """
    from datetime import datetime
    std_log_msg = f"tendemo: {datetime.now().isoformat(timespec='seconds')}: [{level}]: {msg}"
    if (do_print):
        print(std_log_msg)
    std_log_msg += "\n"
    with open(filenanme, 'a') as fo:
        fo.write(std_log_msg)

# create dir if not exist
def checkDir(dirname):
    import os
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return 0

# generater timetag for lrc files, in [mm:ss.xx] format
def lrc_time_conveter(time_in_ms):
    time_in_s = int(time_in_ms/1000)
    return f"{(str(int(time_in_s/60))).zfill(2)}:{(str(time_in_s%60)).zfill(2)}.{(str(int((time_in_ms%1000)/10))).zfill(2)}"

class tenRequest(object):

    def __init__(self, time_offset=0):
        from pathlib import PurePath
        # self.__file_path = audio_file_name
        # pathobj = PurePath(self.__file_path)
        # self.__file_name = pathobj.parts[-1]
        self.__file_size = 0
        self.__slice_num = 1
        self.__time_offset = time_offset
        self.__keywords = ""
        self.language = ""
        self.query_string = ""
        self.res_json = {}
        stg_log(f"Ten Request init done")

    # Read config from file
    def loadConfig(self, configfile = "config.json"):
        import json
        with open(configfile) as fi:
            configobj = json.load(fi)
            self.__appid = configobj["ten_id"]
            self.__secret_key = configobj["ten_key"]
        stg_log(f"loadConfig: loaded")
        return 0

    # Set language & model
    def loadLanguage(self, language="zh", model="16k"):
        if language in lang_supported:
            self.language = f"{model}_{language}"
        else:
            self.language = "16k_zh"
        stg_log(f"loadLanguage: {self.language}")
        return 0

    # check the file and calculate slice amount
    # useless in online-file mode
    # def preCheck(self):
    #     import os
    #     self.__file_size = os.path.getsize(self.__file_path)
    #     self.__slice_num = int(self.__file_size/(size5m)) + 1
    #     stg_log(f"preCheck done file_name: {self.__file_path}, file_size: {str(self.__file_size)}, slice_num: {str(self.__slice_num)}")
        # return 0

    # Header in json object
    def prepareRequestheader(self):
        self.request_header = {
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Host": "asr.tencentcloudapi.com"
        }
        stg_log(f"raw header: {json.dumps(self.request_header)}")
        return 0

    # Unix timestamp in ms as str
    def prepareTimestamp(self):
        import datetime
        now_time = datetime.datetime.now()
        self.now_stamp = str(int(now_time.timestamp()))
        stg_log(f"timestamp: {self.now_stamp}")
        return 0


    # Follow standard v3: https://cloud.tencent.com/document/product/1093/35641
    def generateSign(self):
        """
        Generate signature based on request parameters.
        Things below are required in param dict:
        RequestMethod: HTTP request method;
        URI: URI param;
        QueryString: QueryString in URI, set as void string in POST requests;
        HeaderDict: Headers & values, in string;
        HeaderList: Headers, in string;
        RequestBody: Body in the request, set as void string in GET requests;
        """
        import hashlib, hmac
        import datetime
        from datetime import timezone
        # step 1
        header_pair_string = ""
        header_key_string = ""

        header_pair_dict = self.request_header
        header_key_list = [k for k in header_pair_dict.keys()]

        for every_header_key in header_key_list:
            header_key_string += f"{every_header_key};"
            header_pair_string += f"{every_header_key}:{header_pair_dict.get(every_header_key)}\n"
        header_key_string = header_key_string[0:-1]

        header_pair_string = header_pair_string.lower()
        header_key_string = header_key_string.lower()

        # query_string = json.dumps(param_dict.get("request_body"))
        query_string = ""
        query_hash_obj = hashlib.sha256(query_string.encode('utf8'))
        query_hash_str = query_hash_obj.hexdigest()
        s1_string = request_method + "\n" +\
                    api_url + "\n" +\
                    self.query_string + "\n" +\
                    header_pair_string + "\n" +\
                    header_key_string + "\n" +\
                    query_hash_str
        stg_log(f"s1 string: {s1_string}")

        # step 2
        # now_time = datetime.datetime.now()
        # Date must be in utc time
        utc_time = datetime.datetime.utcnow()

        # date ! date ! 
        # now_date = ""
        # utc_time = utc_time.replace(tzinfo= timezone.utc)
        utc_date = utc_time.strftime("%Y-%m-%d")
        the_scope = f"{utc_date}/{service_name}/{end_mark}"

        s1_hash_obj = hashlib.sha256(s1_string.encode('utf8'))
        s1_hash_str = s1_hash_obj.hexdigest()

        s2_string = sign_algo_name + "\n" +\
            self.now_stamp + "\n"  +\
            the_scope + "\n"  +\
            s1_hash_str
        stg_log(f"s2 string: {s2_string}")

        # step 3

        # Read secret key
        k1_hmac_key= "TC3" + self.__secret_key
        k1_hmac_string = utc_date
        b_key = str.encode(k1_hmac_key) # to bytes
        # Obj in bytes as new key
        k1_hmac_obj = hmac.new(b_key, k1_hmac_string.encode('utf8'), "sha256")

        k2_hmac_obj = hmac.new(k1_hmac_obj.digest(), service_name.encode('utf8'), "sha256")

        k3_hmac_obj = hmac.new(k2_hmac_obj.digest(), "tc3_request".encode('utf8'), "sha256")

        s3_signature_object = hmac.new(k3_hmac_obj.digest(), s2_string.encode('utf8'), "sha256")
        s3_string = s3_signature_object.hexdigest()
        stg_log(f"s3 string: {s3_string}")

        # step4

        s4_string = sign_algo_name +" " +\
            f"Credential={self.__appid}/{the_scope}," +" " +\
            f"SignedHeaders={header_key_string}," +" " +\
            f"Signature={s3_string}"
        
        stg_log(f"s4 string: {s4_string}")
        self.auth_sign = s4_string
        return 0

    # Process the request
    def uploadTask(self):
        import requests
        final_url = f"https://{api_host}{api_url}?{self.query_string}"
        upload_request = requests.get(final_url, headers=self.request_header)
        # print(upload_request.text)
        preview_text = upload_request.text
        preview_text = preview_text[0:200]
        stg_log(f"Response: {preview_text}")
        self.res_json = upload_request.json()
        return upload_request.json()



class uploadAudio(tenRequest):

    def __init__(self):
        tenRequest.__init__(self)

    # like "param1=value1&param2=value2"
    def prepareQuerystring(self, url_raw, keyword_id):
        from urllib import parse
        file_url_encoded = parse.quote(url_raw, safe="")
        # self.query_string = f"Action={api_action}&Version={api_version}&ChannelNum=1&" +\
        #     f"EnginemodelType={self.__language}&ResTextFormat=0&SourceType=0&Url={file_url_encoded}"
        if keyword_id == "n":
            self.query_string = f"ChannelNum=1&" +\
                f"EngineModelType={self.language}&ResTextFormat=0&SourceType=0&Url={file_url_encoded}"
        else:
            self.query_string = f"ChannelNum=1&HotwordId={keyword_id}&" +\
                f"EngineModelType={self.language}&ResTextFormat=0&SourceType=0&Url={file_url_encoded}"
        stg_log(f"query string: {self.query_string}")
        return 0

    def expandHeader(self):
        self.request_header["X-TC-Action"] = up_api_action
        self.request_header["X-TC-Version"] = up_api_version
        self.request_header["X-TC-Timestamp"] = self.now_stamp
        self.request_header["Authorization"] = self.auth_sign
        stg_log(f"expandedHeader: {json.dumps(self.request_header)}")
        return 0

class queryResult(tenRequest):

    def __init__(self):
        tenRequest.__init__(self)

    def prepareQuerystring(self, task_id):
        self.query_string = f"TaskId={task_id}"
        stg_log(f"query string: {self.query_string}")
        return 0

    def expandHeader(self):
        self.request_header["X-TC-Action"] = res_api_action
        self.request_header["X-TC-Version"] = res_api_version
        self.request_header["X-TC-Timestamp"] = self.now_stamp
        self.request_header["Authorization"] = self.auth_sign
        stg_log(f"expandedHeader: {json.dumps(self.request_header)}")
        return 0

    # TBD: Check dir
    def writeFinalResult(self, exp_file_name = "tendemoexp.txt"):
        res_response = self.res_json.get("Response")
        res_data = res_response.get("Data")
        res_text = res_data.get("Result")
        checkDir("export")
        with open(f"./export/{exp_file_name}", 'w') as fo:
            fo.write(res_text)
        stg_log(f"wrote to file: done")
        return 0

def loadArgs():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--filename',
        required=True,
        type=str,
        help="Location of the file, required"
    )
    parser.add_argument(
        '-l',
        '--language',
        required=False,
        default='zh',
        type=str,
        help="Language of the audio, optional, default: zh"
    )
    # keywords txt upload & use
    parser.add_argument(
        '-k',
        '--keyword',
        required=False,
        default='n',
        type=str,
        help="Keyword list ID, optional"
    )
    parser.add_argument(
        '-m',
        '--model',
        required=False,
        default='16k',
        type=str,
        help="Engine model, optional, default: 16k"
    )
    # parser.add_argument(
    #     '-a'
    # )
    return parser

def main():
    # tenobj = tendemo()
    # tenobj.loadConfig()
    # tenobj.loadLanguage()

    # tenobj.prepareQuerystring()
    # tenobj.prepareRequestheader()
    # tenobj.prepareTimestamp()

    # tenobj.generateSign()
    # tenobj.expandHeader()
    # tenobj.uploadTask()

    # tenobj.taskQuerystring()
    # tenobj.prepareRequestheader()
    # tenobj.prepareTimestamp()

    # tenobj.generateSign()
    # tenobj.expandHeader()
    # tenobj.uploadTask()

    # extract parameters
    args = loadArgs().parse_args()
    # Remove spaces
    arg_link = args.filename
    arg_link = arg_link.replace(" ", "")
    arg_lang = args.language
    arg_lang = arg_lang.replace(" ", "")
    arg_model = args.model
    arg_model = arg_model.replace(" ", "")
    arg_keyword = args.keyword
    arg_keyword = arg_keyword.replace(" ", "")

    arg_link_split = arg_link.split("/")
    arg_file_name = arg_link_split[-1]

    upObj = uploadAudio()

    upObj.loadConfig()
    upObj.loadLanguage(language=arg_lang, model=arg_model)

    upObj.prepareQuerystring(url_raw=arg_link, keyword_id=arg_keyword)
    upObj.prepareRequestheader()
    upObj.prepareTimestamp()

    upObj.generateSign()
    upObj.expandHeader()

    # TBD: handle err
    up_res = upObj.uploadTask()
    up_res_response = up_res.get("Response")
    up_res_data = up_res_response.get("Data")
    up_task_id = up_res_data.get("TaskId")

    rsObj = queryResult()


    rsObj.loadConfig()
    # rsObj.loadLanguage()

    rsObj.prepareQuerystring(up_task_id)
    rsObj.prepareRequestheader()
    rsObj.prepareTimestamp()

    rsObj.generateSign()
    rsObj.expandHeader()

    # qu_res_text = ""
    while True:
        time.sleep(30)
        qu_res = rsObj.uploadTask()
        qu_res_response = qu_res.get("Response")
        qu_res_data = qu_res_response.get("Data")

        # or: =="success"
        if qu_res_data.get("StatusStr") != "doing":
            # qu_res_text = qu_res_data.get("Result")
            break

        stg_log(f"Still converting...")

    stg_log(f"Result get")
    rsObj.writeFinalResult(arg_file_name + ".txt")
    # print(qu_res_text)
    print("done...")

if __name__ == "__main__":
    main()