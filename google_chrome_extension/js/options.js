function saveOptions(){
			var instapaper_account = document.getElementById("instapaper_account");
			var instapaper_password = document.getElementById("instapaper_password");

			localStorage["instapaper_account"]=instapaper_account.value;
			localStorage["instapaper_password"]=instapaper_password.value;

			var status= document.getElementById("status");
			status.innerHTML="Options saved";

			setTimeout(function(){
				status.innerHTML="";
		},1050);
}
function restoreOptions(){
			var instapaper_account = localStorage["instapaper_account"];
			var instapaper_password = localStorage["instapaper_password"];

			if (instapaper_account === undefined ){
				instapaper_account = "";
			}
			if (instapaper_password === undefined ){
				instapaper_password = "";
			}
			
			document.getElementById("instapaper_account").value=instapaper_account;
			document.getElementById("instapaper_password").value=instapaper_password;
}
