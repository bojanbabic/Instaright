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
	backendResponse:"",
	init: function(){
		var ver = -1; firstrun = true;
                var cur;
                var error = false;
                var timer = Components.classes["@mozilla.org/timer;1"]
                                    .createInstance(Components.interfaces.nsITimer);

                try{
                        Components.utils.import('resource://gre/modules/AddonManager.jsm');
                        AddonManager.getAddonByID("{1d682819-bef2-4a75-8ffa-adf3733f5557}", function(addon){
                               cur=addon.version;

                        });
                        var thread = Components.classes["@mozilla.org/thread-manager;1"]
                                        .getService(Components.interfaces.nsIThreadManager)
                                        .currentThread;
                        while (!cur){
                                thread.processNextEvent(true);
                        }
                }catch(e){
                        try{
                                var gExtensionManager = Components.classes["@mozilla.org/extensions/manager;1"]
                                      .getService(Components.interfaces.nsIExtensionManager);
                                cur=gExtensionManager.getItemForID("{1d682819-bef2-4a75-8ffa-adf3733f5557}").version;  
                        }catch(ee){
                                error=true;
                        }
                }
                if (error){
                        return;
                }
		try{
			ver = this.prefs.getCharPref("version");
			firstrun = this.prefs.getBoolPref("firstrun");
                	var string_bundle = document.getElementById("instaright_bundle");
	                com.appspot.instaright.alert_instaright = string_bundle.getString('alert_instaright');
                	com.appspot.instaright.alert_invalid_mail = string_bundle.getString('alert_invalid_email');
                	com.appspot.instaright.alert_save_disabled = string_bundle.getString('alert_save_disabled');
                	com.appspot.instaright.alert_no_url = string_bundle.getString('alert_no_url');
                	com.appspot.instaright.alert_success = string_bundle.getString('alert_success');
                	com.appspot.instaright.alert_bad_request = string_bundle.getString('alert_bad_request');
                	com.appspot.instaright.alert_invalid_credential = string_bundle.getString('alert_invalid_credential');
                	com.appspot.instaright.alert_service_error = string_bundle.getString('alert_service_error');
                	com.appspot.instaright.alert_onek= string_bundle.getString('alert_onek');
                	com.appspot.instaright.alert_fivek= string_bundle.getString('alert_fivek');
                	com.appspot.instaright.alert_tenk= string_bundle.getString('alert_tenk');
                	com.appspot.instaright.alert_thanks = string_bundle.getString('alert_thanks');
                	com.appspot.instaright.alert_sl = string_bundle.getString('alert_sl');
                	com.appspot.instaright.alert_ny = string_bundle.getString('alert_ny');
                	com.appspot.instaright.alert_trophy = string_bundle.getString('alert_trophy');
                	com.appspot.instaright.alert_hny = string_bundle.getString('alert_hny');
                	com.appspot.instaright.alert_usage = string_bundle.getString('alert_usage');
			
		}catch(e){
		}finally{
                        try{
                                if (firstrun){
                                        this.prefs.setBoolPref("firstrun",false);
                                        this.prefs.setCharPref("version",cur);
                                        com.appspot.instaright.sendAlert("chrome://instaright/skin/instapaper_mod.png",
                                                com.appspot.instaright.alert_instaright, com.appspot.instaright.alert_thanks);
                                        timer.initWithCallback(function(){
                                                        gBrowser.selectedTab = gBrowser.addTab("https://addons.mozilla.org/en-US/firefox/addon/13317");
                                                        }, 1500, Components.interfaces.nsITimer.TYPE_ONE_SHOT);
                                }
                                if (ver != cur && !firstrun){
                                        this.prefs.setCharPref("version",cur);
                                        com.appspot.instaright.sendAlert("chrome://instaright/skin/instapaper_mod.png",
                                                com.appspot.instaright.alert_instaright, com.appspot.instaright.alert_thanks);
                                        timer.initWithCallback(function(){
                                                        gBrowser.selectedTab = gBrowser.addTab("https://addons.mozilla.org/en-US/firefox/addon/13317");
                                                        }, 1500, Components.interfaces.nsITimer.TYPE_ONE_SHOT);
                                }
                        } catch(e){
				alert('ee:'+e);
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
					    this.updateLoginInfo(loginInfo, this.account, password);

				    } catch(e){
					    //alert(e);
				    }
		
	},
	updateLoginInfo: function( loginInfo, account, password){
					    // if already exists modify myLoginManager.modifyLogin(oldLogin, newLogin)
					    existingLogin = this.getLoginInfoForUsername(account); 
					    if ( existingLogin == null && password != ""){
						    this.myLoginManager.addLogin(loginInfo);
					    } 
					    else if ( password == "" && existingLogin != null){
						    this.myLoginManager.removeLogin(existingLogin);
					    }
					    else if ( existingLogin != null){
						    this.myLoginManager.removeLogin(existingLogin);
						    this.myLoginManager.addLogin(loginInfo);
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
                //TODO why this can be null?
                if (menu != null){
		        menu.addEventListener("itemShowing", this.itemShowing, false);
                }
	},
	itemShowing: function(){
		menuItem = document.getElementById("instaright");
                //TODO why this can be null?
                if (menuItem != null){
		        menuItem.hidden = !gContextMenu.onLink;
                }
	}	
}

com.appspot.instaright={
	_SERVER:"http://instaright.appspot.com",
	//_SERVER:"http://localhost:8080",
        alertService:null,
        alert_instaright:"",
        alert_invalid_mail:"",
        alert_save_disabled:"",
        alert_no_url:"",
        alert_success:"",
        alert_bad_request:"",
        alert_invalid_credential:"",
        alert_service_error:"",
	alert_thanks:"",
	alert_onek:"",
	alert_fivek:"",
	alert_tenk:"",
        alert_sl:"",
        alert_ny:"",
        alert_hny:"",
        alert_trophy:"",
	alert_status:"",
	alert_message:"",
	alert_icon:"",
	alert_usage:"",
	setAlert:function(alert_message){
		if (com.appspot.model.backendResponse == ''){
			this.alert_status=this.alert_instaright;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/instapaper_mod.png";
		}
		else if (com.appspot.model.backendResponse == 'hny'){
			this.alert_status=this.alert_hny;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/hny.png";
		}
		else if (com.appspot.model.backendResponse == '1000'){
			this.alert_status=this.alert_onek;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/onek.png";
		}
		else if (com.appspot.model.backendResponse == '5000'){
			this.alert_status=this.alert_fivek;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/fivek.png";
		}
		else if (com.appspot.model.backendResponse == '10000'){
			this.alert_status=this.alert_tenk;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/tenk.png";
		}
		else if (com.appspot.model.backendResponse == '1'){
			this.alert_status=this.alert_trophy;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/dfirst.png";
		}
		else if (com.appspot.model.backendResponse == '2'){
			this.alert_status=this.alert_trophy;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/dsecond.png";
		}
		else if (com.appspot.model.backendResponse == '3'){
			this.alert_status=this.alert_trophy;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/dthird.png";
		}
		else if (com.appspot.model.backendResponse == '5'){
			this.alert_status=this.alert_usage;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/5usage.png";
		}
		else if (com.appspot.model.backendResponse == '25'){
			this.alert_status=this.alert_sl;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/sl25.png";
		}
		else if (com.appspot.model.backendResponse == '55'){
			this.alert_status=this.alert_sl;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/sl55.png";
		}
		else if (com.appspot.model.backendResponse == '65'){
			this.alert_status=this.alert_sl;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/sl65.png";
		}
		else if (com.appspot.model.backendResponse == '105'){
			this.alert_status=this.alert_sl;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/sl105.png";
		}
		else if (com.appspot.model.backendResponse == 'ny'){
			this.alert_status=this.alert_ny;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/ny.png";
		}
                else {
			this.alert_status=this.alert_instaright;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/instapaper_mod.png";
		}
	},
        sendAlert:function(badge, alert_title, alert_message){
                if (this.alertService == null){
                        try{
		                this.alertService = Components.classes["@mozilla.org/alerts-service;1"].  
			                getService(Components.interfaces.nsIAlertsService);  
                        }catch(e){
                                this.alertService = null;
                        }
                }
                if (this.alertService != null){
			this.setAlert(alert_message);
			this.alertService.showAlertNotification(this.alert_icon,this.alert_status,alert_message,
				false, "", null, "");  
                }else{
                        alert(alert_message);
                }

        },
	start:function(){
		com.appspot.model.startup();
		if (com.appspot.model.account == "" || com.appspot.model.account == null){
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png",   
                                        this.alert_instaright, this.alert_invalid_mail);
			return;
		}
		if (!gContextMenu) { // Mysterious error console
			return;
		}	
		textSelected = null;
                title = null;
		if (gContextMenu.onLink){
			url=gContextMenu.link.href;
		} else if (!com.appspot.model.disablePageSaveMode){
			url = window.top.getBrowser().selectedBrowser.contentWindow.location.href;
                        title = content.document.title;
		} else {
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png",this.alert_instaright, this.alert_save_disabled);
			return;
		}
		if (url == null){
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png", this.alert_instaright, this.alert_no_url);
			this.logErrors("Can't determine link , try another");
			return;
		}
		// text javascript url fix
		if (url.indexOf('javascript') == 0 || url.indexOf('mailto') == 0 || url.indexOf('about:blank') != -1){
			//add javascript or mailto into description
			// TODO this can overwrite selected text if mouse is over malto or javascript link
			textSelected = url;
			url = window.top.getBrowser().selectedBrowser.contentWindow.location.href;
                        title = content.document.title;
		}
		if (textSelected == null){
			textSelected = this.getSelectedText();
		}
		this.sendUrlSynchAjax(url, title, textSelected);
		// crazy check that is necessary for linux vs windows firefox
		if (com.appspot.model.ajaxResponse == '201' && (com.appspot.model.disableAlert == false || com.appspot.model.disableAlert == "false" )){
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png", this.alert_instaright, this.alert_success);
		}
		else if (com.appspot.model.ajaxResponse == '400'){
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png", this.alert_instaright, this.alert_bad_request);
		}
		else if (com.appspot.model.ajaxResponse == '403'){
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png", this.alert_instaright, this.alert_invalid_credential);
		}
		else if (com.appspot.model.ajaxResponse == '500'){
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png", this.alert_instaright, this.alert_service_error);
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

	sendUrlSynchAjax:function(url, title, textSelected){
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
                                 if ( title != null){
                                         params += "&title="+encodeURIComponent(title);
                                 }

				 loggingLocation = this._SERVER+"/rpc";
                                 response=0;

				 try{
					 logging = new XMLHttpRequest();
					 body = "[";
					 body+="\""+com.appspot.model.account+"\"";
					 body+=",";
					 body+="\""+encodeURIComponent(url)+"\"";
					 body+=",";
					 body+="\""+encodeURIComponent(title)+"\"";
					 body+="]";

					 logging.open('POST', loggingLocation, true);
					 logging.onreadystatechange = function() {
						 if(logging.readyState == 4 && logging.status == 200) {
							 response = null;
							 try {
					                         com.appspot.model.backendResponse=logging.responseText;
							 } catch (e) {
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
