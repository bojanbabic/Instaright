if (!com) var com={};
if (!com.appspot) com.appspot={};
if (!com.appspot.instaright) com.appspot.instaright={};
if (!com.appspot.model) com.appspot.model={}

com.appspot.model={
	prefs: Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService).getBranch("extension.instaright."),
	account: "",
	password: "",
	hostname: "http://www.instapaper.com",
	formSubmitURL: "http://www.instapaper.com/user/login",
	httprealm : null,
	myLoginManager : Components.classes["@mozilla.org/login-manager;1"].getService(Components.interfaces.nsILoginManager),
	disableAlert: false,
	disablePageSaveMode: false,
	targetUrl:"",
	ajaxResponse:"",
	init: function(){
		var ver = -1; firstrun = true;

		gExtensionManager = Components.classes["@mozilla.org/extensions/manager;1"]  
			.getService(Components.interfaces.nsIExtensionManager);
		current = gExtensionManager.getItemForID("instaright@appspot.com").version;
		try{
			ver = this.prefs.getCharPref("version");
			firstrun = this.prefs.getBoolPref("firstrun");

		}catch(e){
			//nothing
		}finally{
			if (firstrun){
				this.prefs.setBoolPref("firstrun",false);
				this.prefs.setCharPref("version",current);

				window.setTimeout(function(){
					gBrowser.selectedTab = gBrowser.addTab("https://addons.mozilla.org/en-US/firefox/addon/13317");
				}, 1500);
			}
			if (ver != current && !firstrun){
				window.setTimeout(function(){
					gBrowser.selectedTab = gBrowser.addTab("https://addons.mozilla.org/en-US/firefox/addon/13317");
				}, 1500);
			}
		}
		window.removeEventListener("load", function(){ com.appspot.model.init(); }, true);
	},
	menu: null,
	startup: function(){
		this.prefs.QueryInterface(Components.interfaces.nsIPrefBranch2);
		this.prefs.addObserver("", this, false);
		
		this.account= this.prefs.getCharPref("account").toLowerCase();
		loginInfo = this.getLoginInfoForUsername(this.account);
		if ( loginInfo != null){
			this.password = loginInfo.password;
                        pwdElement = document.getElementById("accountPassword");
                        // if options pannel in opened - set password
                        if (pwdElement !== undefined && pwdElement != null){
                                document.getElementById("accountPassword").value = loginInfo.password;
                        }

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
				this.refreshInformation(this.password);
		    case "disablePageSaveMode":
				this.disablePageSaveMode = this.prefs.getBoolPref("disablePageSaveMode");
				this.refreshInformation(this.password);
		    case "disableAlert":
				this.disableAlert = this.prefs.getBoolPref("disableAlert");
				this.refreshInformation(this.password);
				break;
		}		
	},
	refreshInformation: function(password){
				   this.disableAlert;
				   this.disablePageSaveMode;
				   try{
					    if (password == null){
						password = this.password;
					    }
					    nsLoginInfo = new Components.Constructor("@mozilla.org/login-manager/loginInfo;1",  Components.interfaces.nsILoginInfo,  "init");  
					    loginInfo = new nsLoginInfo('http://www.instapaper.com',  'http://www.instapaper.com/user/login', null,  this.account, password, 'username', 'password');  
				            //alert('about to modify login info - username:'+ this.account + ' password:' + password );
					    this.updateLoginInfo(loginInfo, this.account, password);

				    } catch(e){
					    //alert(e);
				    }
		
	},
	updateLoginInfo: function( loginInfo, account, password){
					    // if already exists modify myLoginManager.modifyLogin(oldLogin, newLogin)
					    existingLogin = this.getLoginInfoForUsername(account); 
					    if ( existingLogin == null && password != ""){
						    //alert('new login info');
						    this.myLoginManager.addLogin(loginInfo);
					    } 
					    else if ( password == "" && existingLogin != null){
						    //alert('removing empty pass login');
						    this.myLoginManager.removeLogin(existingLogin);
					    }
					    else if ( existingLogin != null){
						    //alert('updated user login info');
						    this.myLoginManager.removeLogin(existingLogin);
						    this.myLoginManager.addLogin(loginInfo);
						    //myLoginManager.modifyLogin(existingLogin, loginInfo);
					    }
		
	},
	getLoginInfoForUsername: function(username){
		try{
			hostname = "http://www.instapaper.com";
			formSubmitURL = "http://www.instapaper.com/user/login";
			logins = this.myLoginManager.findLogins({}, this.hostname, this.formSubmitURL, this.httprealm);

			for (i=0; i< logins.length; i++){
				if (logins[i].username == username){
					return logins[i];
				}
			}
			return null;
		} catch(e){
			//alert(e);
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
		com.appspot.model.startup();
		alertsService = Components.classes["@mozilla.org/alerts-service;1"].  
			getService(Components.interfaces.nsIAlertsService);  
		if (com.appspot.model.account == "" || com.appspot.model.account == null){
			alertsService.showAlertNotification("chrome://instaright/skin/instapaper_mod.png",   
					"Instaright alert", "Invalid email. Please enter valid email in plugin options.",   
					false, "", null, "");  
			//alert('Invalid email. Please enter valid email in plugin options.');
			return;
		}
		if (!gContextMenu) { // Mysterious error console
			return;
		}	
		if (gContextMenu.onLink){
			url=gContextMenu.link.href;
		} else if (!com.appspot.model.disablePageSaveMode){
			url = window.top.getBrowser().selectedBrowser.contentWindow.location.href;
		} else {
			alertsService.showAlertNotification("chrome://instaright/skin/instapaper_mod.png",   
					"Instaright alert", "Page saving mode has been disabled. Please recheck your settings.",   
					false, "", null, "");  
			//alert("Page saving mode has been disabled. Please recheck your settings.");
			return;
		}
		if (url == null){
			alertsService.showAlertNotification("chrome://instaright/skin/instapaper_mod.png",   
					"Instaright alert", "Can\'t determine link... try another!",   
					false, "", null, "");  
			//alert('Can\'t determine link... try another!')
				this.logErrors("Can't determine link , try another");
			return;
		}
		textSelected = null;
		// text javascript url fix
		if (url.indexOf('javascript') == 0 || url.indexOf('mailto') == 0){
			//add javascript or mailto into description
			// TODO this can overwrite selected text if mouse is over malto or javascript link
			textSelected = url;
			url = window.top.getBrowser().selectedBrowser.contentWindow.location.href;
		}
		if (textSelected == null){
			textSelected = this.getSelectedText();
		}
		this.sendUrlSynchAjax(url, textSelected);
		// crazy check that is necessary for linux vs windows firefox
		if (com.appspot.model.ajaxResponse == '201' && (com.appspot.model.disableAlert == false || com.appspot.model.disableAlert == "false" )){
			alertsService.showAlertNotification("chrome://instaright/skin/instapaper_mod.png",   
					"Instaright alert", "Success.",   
					false, "", null, "");  
			//alert('Success.');
		}
		else if (com.appspot.model.ajaxResponse == '400'){
			alertsService.showAlertNotification("chrome://instaright/skin/instapaper_mod.png",   
					"Instaright alert", "Bad request. Missing required parameter.",   
					false, "", null, "");  
			//alert('Bad request. Missing required parameter.');
		}
		else if (com.appspot.model.ajaxResponse == '403'){
			alertsService.showAlertNotification("chrome://instaright/skin/instapaper_mod.png",   
					"Instaright alert", "Invalid username or password.",   
					false, "", null, "");  
			//alert('Invalid username or password.');
		}
		else if (com.appspot.model.ajaxResponse == '500'){
			alertsService.showAlertNotification("chrome://instaright/skin/instapaper_mod.png",   
					"Instaright alert", "The service encountered an error. Please try later again.",   
					false, "", null, "");  
			//alert('The service encountered an error. Please try later again.');
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
                        //alert(e);
                }
        },

	sendUrlSynchAjax:function(url, textSelected){
				 lInfo = com.appspot.model.getLoginInfoForUsername(com.appspot.model.account);
				 // there is nasty bug that when user removes passwprd , password info stays untill ff is restarted
				 // but it doen't effect user experience
				 if ( lInfo != null){
					com.appspot.model.password = lInfo.password;//document.getElementById("accountPassword").value;
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

window.addEventListener("load", function(e) { com.appspot.model.init(); }, true);
