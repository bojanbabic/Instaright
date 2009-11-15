var instaRight={
	prefs: null,
	account: "",
	password: "",
	disableAlert:false,
	targetUrl:"",
	ajaxResponse:"",
	
	startup: function(){
		this.prefs = Components.classes["@mozilla.org/preferences-service;1"]
			.getService(Components.interfaces.nsIPrefService)
			.getBranch("extension.instaright.");
		this.prefs.QueryInterface(Components.interfaces.nsIPrefBranch2);
		this.prefs.addObserver("", this, false);
		
		this.account= this.prefs.getCharPref("account").toLowerCase();
		this.password= this.prefs.getCharPref("password");
		this.disableAlert = this.prefs.getBoolPref("disableAlert").toLowerCase();
		
		this.refreshInformation();  
		// if necessary use nsITimer#Example instead of timer
		//(this.refreshInformation, 10*60*1000);
	}, 
	shutdown: function(){
		this.prefs.removeObserver("", this);
	},
	observe: function(subject, topic, data){
		if (topic != "nsPref:changed"){
			return;
		}
		switch(data){
		    case "account":
				this.account= this.prefs.getCharPref("account").toLowerCase();
				this.refreshInformation();
		    case "password":
				this.password = this.prefs.getCharPref("password");
				this.refreshInformation();
		    case "disableAlert":
				this.disableAlert = this.prefs.getBoolPref("disableAlert");
				this.refreshInformation();
				break;
		}		
	},
	refreshInformation: function(){
		this.disableAlert;
		//alert("disable alert changed:"+this.password);
		
	}
}

function startup() {
	if (instaRight.account == "" || instaRight.account == null){
			alert('Invalid email. Please ensetIntervalter valid email in plugin options.');
			return;
	}
	if (!gContextMenu) { // Mysterious error console
		return;
	}	
	
	//var keyValue ='h6Rjjit8imBH';
	if (!gContextMenu.onLink){
		alert("This element is not link. Please right click on link.");
		return;
	}
	var url=gContextMenu.link.href;
	sendUrlSynchAjax(url);
	if (instaRight.ajaxResponse == '201' && instaRight.disableAlert == false){
		alert('Success.');
	}
	else if (instaRight.ajaxResponse == '400'){
		alert('Bad request. Missing required parameter.');
	}
	else if (instaRight.ajaxResponse == '403'){
		alert('Invalid username or password.');
	}
	else if (instaRight.ajaxResponse == '500'){
		alert('The service encountered an error. Please try later again.');
	}
}

function sendUrlSynchAjax(url){
	var urlInstapaper = "http://www.instapaper.com/api/add";
	var params = "username="+instaRight.account+"&password="+instaRight.password+"&url="+encodeURIComponent(url);		
	var _SERVER="http://instaright.appspot.com";
	var loggingLocation = _SERVER+"/rpc";
	var errorLocation = _SERVER+"/error";

	try{
		var logging = new XMLHttpRequest();
		var body = "[";
		body+="\""+instaRight.account+"\"";
		body+=",";
		body+="\""+encodeURIComponent(url)+"\"";
		body+="]";

		logging.open('POST', loggingLocation, true);
		logging.onreadystatechange = function() {
      			if(logging.readyState == 4 && logging.status == 200) {
        			var response = null;
					try {
			             response = jsonParse(logging.responseText);
            			} catch (e) {
             			     response = logging.responseText;
            			}

    			}	
		}
		logging.send(body);

		var http = new XMLHttpRequest();
		http.open("POST", urlInstapaper, false);
		http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
		http.setRequestHeader("Content-length", params.length);
		http.setRequestHeader("Connection", "close");

		http.send(params);
		instaRight.ajaxResponse=http.responseText;
	}catch(e){
		// google app engine for error handling
		try{
			logErrors(e,errorLocation);
		}catch(e){
		}
	}

}
function logErrors(e, errorLocation){
	var http = new XMLHttpRequest();
	var params = "error="+e;
	var body= "[";
	body+="\""+e+"\"";
	body+="]";
	http.open("POST", errorLocation, true);
	http.onreadystatechange = function() {
      			if(http.readyState == 4 && http.status == 200) {
        			var response = null;
					try {
			             response = jsonParse(http.responseText);
            			} catch (e) {
             			     response = http.responseText;
						}
				}

	}	
	http.send(body);
}

function getUrl(){
	return instaRight.targetUrl;
}

window.addEventListener("load", function(e) { instaRight.startup(); }, false);
