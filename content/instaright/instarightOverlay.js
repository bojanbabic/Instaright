if (!com) var com={};
if (!com.appspot) com.appspot={};
if (!com.appspot.instaright) com.appspot.instaright={};
if (!com.appspot.model) com.appspot.model={}

com.appspot.model={
	prefs: null,
	account: "",
	password: "",
	hostname: "http://www.instapaper.com",
	formSubmitURL: "http://www.instapaper.com/user/login",
	disableAlert: false,
	disablePageSaveMode: false,
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
		loginInfo = this.getLoginInfoForUsername(this.account);
		if ( loginInfo != null){
			this.password = loginInfo.password;
		}
		this.disableAlert = this.prefs.getBoolPref("disableAlert");
		this.disablePageSaveMode = this.prefs.getBoolPref("disablePageSaveMode");
		
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
		    case "disablePageSaveMode":
				this.disablePageSaveMode = this.prefs.getBoolPref("disablePageSaveMode");
				this.refreshInformation();
		    case "disableAlert":
				this.disableAlert = this.prefs.getBoolPref("disableAlert");
				this.refreshInformation();
				break;
		}		
	},
	refreshInformation: function(){
				   this.disableAlert;
				   this.disablePageSaveMode;
				    //alert("password changed:"+this.password);
				    //alert("disable alert changed:"+this.disableAlert);
				    try{
					    alert("update password manager:");
					    nsLoginInfo = new Components.Constructor("@mozilla.org/login-manager/loginInfo;1",  Components.interfaces.nsILoginInfo,  "init");  
					    loginInfo = new nsLoginInfo('http://www.instapaper.com',  'http://www.instapaper.com/user/login', null,  this.account, this.password, 'username', 'password');  
						    myLoginManager = Components.classes["@mozilla.org/login-manager;1"].getService(Components.interfaces.nsILoginManager);

					    // if already exists modify myLoginManager.modifyLogin(oldLogin, newLogin)
					    existingLogin = this.getLoginInfoForUsername(this.account); 
					    if ( existingLogin == null && this.password != ""){
						    alert('new login info');
						    myLoginManager.addLogin(loginInfo);
					    } 
					    else if ( this.password == "" && existingLogin != null){
						    alert('removing empty pass login');
						    myLoginManager.removeLogin(existingLogin);
					    }
					    else if ( existingLogin != null){
						    alert('updated user login info');
						    myLoginManager.modifyLogin(existingLogin, loginInfo);
					    }
				    } catch(e){
					    alert(e);
				    }
		
	},
	getLoginInfoForUsername: function(username){
		try{
			hostname = "http://www.instapaper.com";
			formSubmitURL = "http://www.instapaper.com/user/login";
			httprealm = null;
			myLoginManager = Components.classes["@mozilla.org/login-manager;1"].getService(Components.interfaces.nsILoginManager);
			logins = myLoginManager.findLogins({}, hostname, formSubmitURL, httprealm);

			alert('logins size: ' + logins.length);
			alert('looking for username: ' + username);
			for (i=0; i< logins.length; i++){
				if (logins[i].username == username){
					alert('found login info in manager for ' + username);
					return logins[i];
				}
				alert('skipping login info: ' + logins[i].username);
			}
			return null;
		} catch(e){
			alert(e);
		}		
	},

	showItem: function(){
		menu = document.getElementById("contentAreaContextMenu");
		menu.addEventListener("itemShowing", this.itemShowing, false);
	},
	itemShowing: function(){
		menuItem = document.getElementById("instaright");
		menuItem.hidden = !gContextMenu.onLink;
	}	
}

com.appspot.instaright={
	_SERVER:"http://instaright.appspot.com",
	//_SERVER:"http://localhost:8080",
	start:function(){
		if (com.appspot.model.account == "" || com.appspot.model.account == null){
			alert('Invalid email. Please enter valid email in plugin options.');
			return;
		}
		if (!gContextMenu) { // Mysterious error console
			return;
		}	
		if (gContextMenu.onLink){
			url=gContextMenu.link.href;
			//alert("This element is not link. Please right click on link.");
			//return;
		} else if (!com.appspot.model.disablePageSaveMode){
			url = window.top.getBrowser().selectedBrowser.contentWindow.location.href;
		} else {
			alert("Page saving mode has been disabled. Please recheck your settings.");
			return;
		}
		if (url == null){
			alert('Can\'t determine link... try another!')
			this.logErrors("Can't determine link , try another");
			return;
		}
		textSelected = this.getSelectedText();
		this.sendUrlSynchAjax(url, textSelected);
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
	getSelectedText:function(){
                try{
			focusedWindow = document.commandDispatcher.focusedWindow;
			selectedText = focusedWindow.getSelection();
			if (selectedText == null || selectedText == ""){
				return null;
			}
			sText = selectedText.getRangeAt(0);
			return sText;
                } catch(e){
                        alert(e);
                }
        },

	sendUrlSynchAjax:function(url, textSelected){
				 lrnfo = com.appspot.model.getLoginInfoForUsername(com.appspot.model.account);
				 alert('pwd:' + com.appspot.model.password);
				 if ( loginInfo != null){
					com.appspot.model.password = loginInfo.password;
				 } 
				 urlInstapaper = "http://www.instapaper.com/api/add";
				 if (textSelected != null){
					 params = "username="+com.appspot.model.account+"&password="+com.appspot.model.password+"&url="+encodeURIComponent(url)+"&selection="+textSelected;
				 } else {
					 params = "username="+com.appspot.model.account+"&password="+com.appspot.model.password+"&url="+encodeURIComponent(url);
				 }
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
