var instaRight={
	prefs: null,
	account: "",
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
		this.disableAlert = this.prefs.getBoolPref("disableAlert").toLowerCase();
		
		this.refreshInformation();  
		// if necessary use nsITimer#Example instead of timer
		//window.setInterval(this.refreshInformation, 10*60*1000);
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
		    case "disableAlert":
				this.disableAlert = this.prefs.getBoolPref("disableAlert");
				this.refreshInformation();
				break;
		}		
	},
	refreshInformation: function(){
		this.disableAlert;
		//alert("disable alert changed:"+this.disableAlert);
		
	}
}

function startup() {
	if (instaRight.account == "" || instaRight.account == null){
			alert('Invalid email. Please enter valid email in plugin options.');
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
	//while( instaRight.ajaxResponse == '' ){
		
	//}
	//alert(instaRight.disableAlert);
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
	//instaRight.targetUrl=url;
	//TODO uncomment this when you solve url problem 
	//try{
	//var z=content.document.createElement('script');
	//z.setAttribute('src','http://www.instapaper.com/j/pkRp5c0uhD7L');
	//var u ='http://www.instapaper.com/j/h6Rjjit8imBH';
	//content.document.location.href="javascript:void(getUrl))";
	//content.document.body.appendChild(z);
	//}catch(e){
	//alert(e);
	//}
	//using key 
	//var u="http://www.instapaper.com/b?v=4&k="+keyValue+"&u="+encodeURIComponent(url)+"&t="+encodeURIComponent(url)+"&s="+encodeURIComponent("");	
	
	// without using key
	//var u="http://www.instapaper.com/b?v=4&u="+encodeURIComponent(url)+"&t="+encodeURIComponent(url)+"&s="+encodeURIComponent("");	
	
	
	//if (!window.open(u,'t','toolbar=0,resizable=0,status=1,width=250,height=150')){
	//	document.location.href=u;
	//}	
}

function sendUrlSynchAjax(url){
	var urlInstapaper = "http://www.instapaper.com/api/add";
	var params = "username="+instaRight.account+"&url="+encodeURIComponent(url);		
	//var _SERVER="http://127.0.0.1:8080";
	var _SERVER="http://instaright.appspot.com";
	//logging.send(null);
	var body = new Array();
	body.push(instaRight.account);
	body.push(encodeURIComponent(url));
	var bodyJSON=JSON.stringify(body);

	try{
		var logging = new XMLHttpRequest();
//		loc = _SERVER+"/rpc?";
		loc = _SERVER+"/rpc";
		//logging.open('GET', loc+params, true);
		
		logging.open('POST', loc, true);
		logging.onreadystatechange = function() {
      			if(logging.readyState == 4 && logging.status == 200) {
        			var response = null;
					try {
			             response = JSON.parse(logging.responseText);
            			} catch (e) {
             			     response = logging.responseText;
            			}

    			}	
		}
		logging.send(bodyJSON);


		var http = new XMLHttpRequest();
		http.open("POST", urlInstapaper, false);
		http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
		http.setRequestHeader("Content-length", params.length);
		http.setRequestHeader("Connection", "close");

		http.send(params);
		instaRight.ajaxResponse=http.responseText;
	}catch(e){
		// google app engine for error handling
		// alert(e);
	}

}

function getUrl(){
	return instaRight.targetUrl;
}

window.addEventListener("load", function(e) { instaRight.startup(); }, false);
