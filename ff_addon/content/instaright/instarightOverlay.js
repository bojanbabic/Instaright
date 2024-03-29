if (!com) var com={};
if (!com.appspot) com.appspot={};
if (!com.appspot.instaright) com.appspot.instaright={};
if (!com.appspot.instaright.util) com.appspot.instaright.util={};
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
	updateBadgeCache: function(badge){
		longCacheBadges=["1000","5000","10000"];
		fourDayCacheBadges=["hny"];
		oneDayCacheBadges=["1","2","3","25","55","65","105"];
		shortCacheBadges=["ny","5","robot","yen","movie","news","wiki","sports","music"];
		veryShortCacheBadges=["new_domain"];
		if (longCacheBadges.indexOf(badge) != -1){
			var exp = (new Date()).getTime() + 3600 * 24 * 365 * 1000;
			//alert("setting long term cache " + badge + " expires :" + exp);
			this.prefs.setCharPref("badge_cache",badge);
			this.prefs.setCharPref("badge_expiration", exp);
		}
		if (fourDayCacheBadges.indexOf(badge) != -1){
			var exp = (new Date()).getTime() + 3600 * 24 * 4 * 1000;
			//alert("setting 4 day cache " + badge + " expires :" + exp);
			this.prefs.setCharPref("badge_cache",badge);
			this.prefs.setCharPref("badge_expiration", exp);
		}
		else if (oneDayCacheBadges.indexOf(badge) != -1){
			// set midnight
			var exp = new Date();
			exp.setDate(exp.getDate() + 1);
			exp.setHours(0);
			exp.setMinutes(0);
			exp.setSeconds(0);
			//alert("setting 1 day cache " + badge + " expires :" + exp);
			this.prefs.setCharPref("badge_cache",badge);
			this.prefs.setCharPref("badge_expiration", exp.getTime());
		}
		else if (shortCacheBadges.indexOf(badge) != -1 ){
			var exp = (new Date()).getTime() + 60 * 15 * 1000;
			//alert("setting 15min cache " + badge + " expires :" + exp);
			this.prefs.setCharPref("badge_cache",badge);
			this.prefs.setCharPref("badge_expiration", exp.getTime());
		}
		if (veryShortCacheBadges.indexOf(badge) != -1 ){
			var exp = (new Date()).getTime() + 60 * 1 * 1000;
			// alert("setting 1min cache " + badge + " expires :" + exp);
			this.prefs.setCharPref("badge_cache",badge);
			this.prefs.setCharPref("badge_expiration", exp.getTime());
		}
		
	},
        currentVersion:"",
	init: function(){
		var ver = -1; firstrun = true;
                var cur;
                var error = false;
                var timer = Components.classes["@mozilla.org/timer;1"]
                                    .createInstance(Components.interfaces.nsITimer);

		var appcontent = document.getElementById("appcontent");
                try{
                        AddonManager.getAddonByID("{1d682819-bef2-4a75-8ffa-adf3733f5557}", function(addon){
                               cur=addon.version;

                        });
                        var thread = Components.classes["@mozilla.org/thread-manager;1"]
                                        .getService(Components.interfaces.nsIThreadManager)
                                        .currentThread;
                        while (!cur){
                                thread.processNextEvent(true);
                        }
                        this.currentVersion=cur;
                }catch(e){
                        try{
                                var gExtensionManager = Components.classes["@mozilla.org/extensions/manager;1"]
                                      .getService(Components.interfaces.nsIExtensionManager);
                                cur=gExtensionManager.getItemForID("{1d682819-bef2-4a75-8ffa-adf3733f5557}").version;  
                                this.currentVersion=cur;
                        }catch(ee){
                                error=true;
                        }
                }
                if (error){
                        return;
                }
		try{
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
                	com.appspot.instaright.alert_movie = string_bundle.getString('alert_video');
                	com.appspot.instaright.alert_wiki = string_bundle.getString('alert_wiki');
                	com.appspot.instaright.alert_sport = string_bundle.getString('alert_sport');
                	com.appspot.instaright.alert_music = string_bundle.getString('alert_music');
                	com.appspot.instaright.alert_economy = string_bundle.getString('alert_economy');
                	com.appspot.instaright.alert_gadget = string_bundle.getString('alert_gadget');
                	com.appspot.instaright.alert_news = string_bundle.getString('alert_news');
                	com.appspot.instaright.alert_congrats = string_bundle.getString('alert_congrats');
                	com.appspot.instaright.alert_first_message = string_bundle.getString('alert_first_message');
                	com.appspot.instaright.alert_domain = string_bundle.getString('alert_domain');
			firstrun = this.prefs.getBoolPref("firstrun");
			ver = this.prefs.getCharPref("version");
		}catch(e){
		}finally{
                        try{
                                if (firstrun){
                                        this.prefs.setCharPref("version",cur);
					this.prefs.setBoolPref("noBookmarks", true);
                                        com.appspot.instaright.sendAlert("chrome://instaright/skin/instapaper_mod.png",
                                                    com.appspot.instaright.alert_instaright, com.appspot.instaright.alert_thanks);
					// 
                                        this.prefs.setBoolPref("firstrun",false);
                                        timer.initWithCallback(function(){
                                                        gBrowser.selectedTab = gBrowser.addTab("https://addons.mozilla.org/en-US/firefox/addon/13317");
                                                        }, 1500, Components.interfaces.nsITimer.TYPE_ONE_SHOT);
                                }
                                if (ver != cur && !firstrun){
					this.prefs.setBoolPref("noBookmarks", true);
                                        com.appspot.instaright.sendAlert("chrome://instaright/skin/instapaper_mod.png",
                                                 com.appspot.instaright.alert_instaright, com.appspot.instaright.alert_thanks);
                                        this.prefs.setCharPref("version",cur);
                                        timer.initWithCallback(function(){
                                                        gBrowser.selectedTab = gBrowser.addTab("https://addons.mozilla.org/en-US/firefox/addon/13317");
                                                        }, 1500, Components.interfaces.nsITimer.TYPE_ONE_SHOT);
                                }
                        } catch(e){
			//	alert('ee:'+e);
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
	_SERVER:"http://49.latest.instaright.appspot.com",
	//_SERVER:"http://instaright.appspot.com",
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
	alert_economy:"",
	alert_movie:"",
	alert_music:"",
	alert_wiki:"",
	alert_sport:"",
	alert_domain:"",
	alert_gadget:"",
	alert_congrats:"",
	alert_first_message:"",
	setAlert:function(alert_message){
		var firstBookmark = com.appspot.model.prefs.getBoolPref("noBookmarks");
		var firstRun = false;
		try{
			firstRun = com.appspot.model.prefs.getBoolPref("firstrun");
		} catch(e){}
		var version = -1;
		try{
			version = com.appspot.model.prefs.getCharPref("version");
		} catch(e){}
		if (firstBookmark && !firstRun && version == com.appspot.model.currentVersion){
			this.alert_status = this.alert_congrats;
			this.alert_message = this.alert_first_message;

			this.alert_icon = "chrome://instaright/skin/champagne.png";
			com.appspot.model.prefs.setBoolPref("noBookmarks", false);
			return;
		}
		var cachedValue = com.appspot.model.prefs.getCharPref("badge_cache");
		var expires = com.appspot.model.prefs.getCharPref("badge_expiration");
		var now = new Date();
		var exp_time = new Date(parseInt(expires));
		if  (now.getTime() < exp_time.getTime()){
			// just set backend response
			com.appspot.model.backendResponse = cachedValue;
		}
		// based on backend repsonse set icon, status and message
		if (com.appspot.model.backendResponse == ''){
			this.alert_status=this.alert_instaright;
			this.alert_message=alert_message;
			this.alert_icon="chrome://instaright/skin/instapaper_mod.png";
		}
		else if (com.appspot.model.backendResponse == 'hny'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_hny;
			this.alert_icon="chrome://instaright/skin/hny.png";
		}
		else if (com.appspot.model.backendResponse == '1000'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_onek;
			this.alert_icon="chrome://instaright/skin/onek.png";
		}
		else if (com.appspot.model.backendResponse == '5000'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_fivek;
			this.alert_icon="chrome://instaright/skin/fivek.png";
		}
		else if (com.appspot.model.backendResponse == '10000'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_tenk;
			this.alert_icon="chrome://instaright/skin/tenk.png";
		}
		else if (com.appspot.model.backendResponse == '1'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_trophy;
			this.alert_icon="chrome://instaright/skin/dfirst.png";
		}
		else if (com.appspot.model.backendResponse == '2'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_trophy;
			this.alert_icon="chrome://instaright/skin/dsecond.png";
		}
		else if (com.appspot.model.backendResponse == '3'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_trophy;
			this.alert_icon="chrome://instaright/skin/dthird.png";
		}
		else if (com.appspot.model.backendResponse == '5'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_usage;
			this.alert_icon="chrome://instaright/skin/5usage.png";
		}
		else if (com.appspot.model.backendResponse == '25'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_sl;
			this.alert_icon="chrome://instaright/skin/sl25.png";
		}
		else if (com.appspot.model.backendResponse == '55'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_sl;
			this.alert_icon="chrome://instaright/skin/sl55.png";
		}
		else if (com.appspot.model.backendResponse == '65'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_sl;
			this.alert_icon="chrome://instaright/skin/sl65.png";
		}
		else if (com.appspot.model.backendResponse == '105'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_sl;
			this.alert_icon="chrome://instaright/skin/sl105.png";
		}
		else if (com.appspot.model.backendResponse == 'ny'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_ny;
			this.alert_icon="chrome://instaright/skin/ny.png";
		}
		else if (com.appspot.model.backendResponse == 'robot'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_gadget;
			this.alert_icon="chrome://instaright/skin/robot.png";
		}
		else if (com.appspot.model.backendResponse == 'yen'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_economy;
			this.alert_icon="chrome://instaright/skin/yen.png";
		}
		else if (com.appspot.model.backendResponse == 'movie'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_movie;
			this.alert_icon="chrome://instaright/skin/movie.png";
		}
		else if (com.appspot.model.backendResponse == 'news'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_news;
			this.alert_icon="chrome://instaright/skin/news.png";
		}
		else if (com.appspot.model.backendResponse == 'wiki'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_wiki;
			this.alert_icon="chrome://instaright/skin/wiki.png";
		}
		else if (com.appspot.model.backendResponse == 'sport'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_sport;
			this.alert_icon="chrome://instaright/skin/sport.png";
		}
		else if (com.appspot.model.backendResponse == 'music'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_music;
			this.alert_icon="chrome://instaright/skin/music.png";
		}
		else if (com.appspot.model.backendResponse == 'new_domain'){
			this.alert_status=alert_message;
			this.alert_message=this.alert_domain;
			this.alert_icon="chrome://instaright/skin/new_domain.png";
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
			this.alertService.showAlertNotification(this.alert_icon,this.alert_status,this.alert_message,
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
		this.checkResponse();
	},
	checkResponse:function(){
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
	sendFromUrlbar:function(){
		if (com.appspot.model.account == "" || com.appspot.model.account == null){
                        this.sendAlert("chrome://instaright/skin/instapaper_mod.png",   
                                        this.alert_instaright, this.alert_invalid_mail);
			return;
		}
		url = window.top.getBrowser().selectedBrowser.contentWindow.location.href;
                title = content.document.title;
		this.sendUrlSynchAjax(url,title,null);
		this.checkResponse();
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

				 try{

				 loggingLocation = this._SERVER+"/rpc";

					 logging = new XMLHttpRequest();
					 body = "[";
					 body+="\""+com.appspot.model.account+"\"";
					 body+=",";
					 body+="\""+encodeURIComponent(url)+"\"";
					 body+=",";
					 body+="\""+encodeURIComponent(title)+"\"";
					 body+=",";
					 body+="\""+encodeURIComponent(com.appspot.model.currentVersion)+"\"";
					 body+=",";
					 body+="\"firefox\"";
					 body+="]";

					 logging.open('POST', loggingLocation, true);
					 logging.onreadystatechange = function() {
                                                 // catching 0x80004005 (NS ERROR FAILURE) if connection drops unexpectacly
						 try {
						        if(logging.readyState == 4 && logging.status == 200) {
					                         com.appspot.model.backendResponse=logging.responseText;
								 com.appspot.model.updateBadgeCache(logging.responseText);
						        }	
					         } catch (e) {
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
						 this.logErrors("addon version:" + com.appspot.model.currentVersion + " " +e);
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

com.appspot.instaright.util={
    getElementsByClassName:function (parent, className, nodeName, notClassName) {
        var result = [], tag = nodeName||'*', node, seek, i;
        var rightClass = new RegExp( '(^| )'+ className +'( |$)' );
        var wrongClass = new RegExp( '(^| )'+ notClassName +'( |$)' );
        seek = parent.getElementsByTagName( tag );
        for(var i=0; i<seek.length; i++ )
          if( rightClass.test( (node = seek[i]).className ) && !wrongClass.test( (node = seek[i]).className ) )
            result.push( seek[i] );
        return result;
    }      
}


window.addEventListener("load", function(e) { com.appspot.model.init(); }, true);
