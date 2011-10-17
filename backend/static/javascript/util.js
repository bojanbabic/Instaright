var monthNames = [ "January", "February", "March", "April", "May", "June",
	    "July", "August", "September", "October", "November", "December" ];
                        function $(id){
                                return document.getElementById(id);
                        }
                        function clearElement(element){
                                $(element).innerHTML= "";
                        }
                        function setElementValue(element, value){
                                $(element).innerHTML = value;
                        }
                        // Client function that calls a server rpc and provides a callback
                        function doMatchTargetDomain(type, statsForDate) {
                                $('visualisation').innerHTML = "";
                                //onSuccess(	drawVisualization(type, statsForDate));
                        }

                        // Callback for after a successful doAdd
                        function onSuccess(response) {
                                $('visualization').innerHTML= response;
                        }
			function getMonthString(month_int){
				return monthNames[month_int];
			}
			function getMonth3U(month_str){
				return month_str.substring(0,3)
			}
			function getMonth3U_int(month_int){
				return getMonth3U(getMonthString(month_int));
			}

