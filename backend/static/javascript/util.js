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

