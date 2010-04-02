if (!com) var com={};
if (!com.appspot) com.appspot={};
if (!com.appspot.instaright) com.appspot.instaright={};
if (!com.appspot.model) com.appspot.model={}

com.appspot.model={
	prefs: null,
	account: "",
	password: "",
	disableAlert:false,
	targetUrl:"",
	ajaxResponse:"",
	menu: null,
	
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
		this.showItem();
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
		//alert("password changed:"+this.password);
		//alert("disable alert changed:"+this.disableAlert);
		
	},
	showItem: function(){
		alert('yap');
		menu = document.getElementById("contentAreaContextMenu");
		menu.addEventListener("itemShowing", this.itemShowing, false);
	},
	itemShowing: function(){
		alert('yeah');
		menuItem = document.getElementById("instaright");
		menuItem.hidden = !gContextMenu.onLink;
	}	
}

com.appspot.instaright={
	_SERVER:"http://instaright.appspot.com",
	start:function(){
		if (com.appspot.model.account == "" || com.appspot.model.account == null){
			alert('Invalid email. Please ensetIntervalter valid email in plugin options.');
			return;
		}
		if (!gContextMenu) { // Mysterious error console
			return;
		}	

		if (!gContextMenu.onLink){
			alert("This element is not link. Please right click on link.");
			return;
		}
		url=gContextMenu.link.href;
		this.sendUrlSynchAjax(url);
		if (com.appspot.model.ajaxResponse == '201' && com.appspot.model.disableAlert == false){
			alert('Success.');
		}
		else if (com.appspot.model.ajaxResponse == '400'){
			alert('Bad request. Missing required parameter.');
		}
		else if (com.appspot.model.ajaxResponse == '403'){
			alert('Invalid username or password.');
		}
		else if (com.appspot.model.ajaxResponse == '500'){
			alert('The service encountered an error. Please try later again.');
		}
	},
	sendUrlSynchAjax:function(url){
						urlInstapaper = "http://www.instapaper.com/api/add";
						params = "username="+com.appspot.model.account+"&password="+com.appspot.model.password+"&url="+encodeURIComponent(url);		
						loggingLocation = this._SERVER+"/rpc";

						try{
							 logging = new XMLHttpRequest();
							 body = "[";
							 body+="\""+com.appspot.model.account+"\"";
							 body+=",";
							 body+="\""+encodeURIComponent(url)+"\"";
							 body+="]";

							 logging.open('POST', loggingLocation, true);
							 logging.onreadystatechange = function() {
								 if(logging.readyState == 4 && logging.status == 200) {
									 response = null;
									 try {
										 response = jsonParse(logging.responseText);
									 } catch (e) {
										 response = logging.responseText;
									 }

								 }	
							 }
							 logging.send(body);
							 http = new XMLHttpRequest();
							 http.open("POST", urlInstapaper, false);
							 http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
								 http.setRequestHeader("Content-length", params.length);
								 http.setRequestHeader("Connection", "close");

							 http.send(params);
							 com.appspot.model.ajaxResponse=http.responseText;
						 }catch(e){
							 // google app engine for error handling
							 try{
								 this.logErrors(e);
							 }catch(e){
							 }
						 }
	},
	logErrors:function(e){

			  errorLocation = this._SERVER+"/error";
			  http = new XMLHttpRequest();
			  params = "error="+e;
			  body= "[";
			  body+="\""+e+"\"";
			  body+="]";
			  http.open("POST", errorLocation, true);
			  http.onreadystatechange = function() {
				  if(http.readyState == 4 && http.status == 200) {
					  response = null;
					  try {
						  response = jsonParse(http.responseText);
					  } catch (e) {
						  response = http.responseText;
					  }
				  }

			  }
			  http.send(body);
	}
}

window.addEventListener("load", function(e) { com.appspot.model.startup(); }, false);
