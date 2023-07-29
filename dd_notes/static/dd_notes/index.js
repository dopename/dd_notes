function createFormData(json) {
    // Turns JSON into FormData
	let data = new FormData();
	for (var key in json) {
		data.append(key, json[key])
	}
	return data
}

function createPostHeaders() {
    // Create headers from AJAX request
	let csrf = document.querySelector("input[name=csrfmiddlewaretoken]").value;
	let headers = {
		'X-CSRFToken':csrf,
		'X-Requested-With': 'XMLHttpRequest',
	}
	return headers
}

function postFetch(url, form, callback=null) {
    // AJAX post using a form
	let headers = createPostHeaders()
	fetch(url, {
		method: "POST",
		headers: headers,
		body: new FormData(form)
	})
	.then(response => response.json())
	.then(json => {
		if (callback) {
			callback(json)
		}
	})
}

function postFetchWithoutForm(url, formJson, callback=null) {
    // AJAX post with given JSON
	let headers = createPostHeaders()
	fetch(url, {
		method: "POST",
		headers: headers,
		body: createFormData(formJson)
	})
	.then(response => response.json())
	.then(json => {
		if (callback) {
			callback(json)
		}
	})
}

class SideNote {
    constructor(
        table, noteForm, noteFormWrapper, relatedObjectField, 
        noteContainer, url, getParam=null, options={}
    ) {
        this.table = table;
        this.tbody = this.table.querySelector('tbody');
        this.tableParent = this.table.parentNode;
        this.noteForm = noteForm;
        this.noteFormWrapper = noteFormWrapper;
        this.relatedObjectField = relatedObjectField;
        this.noteContainer = noteContainer;
        this.url = url;
        
        if (getParam == null) {
            this.getParam = 'id';
        } else {
            this.getParam = getParam;
        }

        this.options = options;
        this.createNoteFromJson = this.createNoteFromJson.bind(this);

        this.initialize();
    }

    initialize() {
        var rows = Array.from(this.tbody.children);
        var self = this;

        this.noteForm.addEventListener('submit', function(evt) {
            evt.preventDefault();
            postFetch('', noteForm, self.createNoteFromJson);
            noteForm.reset();
        })

        rows.forEach(function(row) {
            if (!(row.id == 'filter-row')) {
                row.addEventListener('click', function() {
                    let id = row.dataset.target;
                    let targetUrl = `${self.url}?${self.getParam}=${id}`;
                    let successCodes = [200];

                    if (self.options.hasOwnProperty('successCodes') && Array.isArray(self.options.successCodes)) {
                        successCodes = self.options.successCodes;
                    }

                    rows.forEach(function(r) {
                        r.style.backgroundColor = "#FFFFFF";
                    })
                    row.style.backgroundColor = "#87CEEB";

                    fetch(targetUrl)
                    .then(response => {
                        if (successCodes.includes(response.status)) {
                            return response.json();
                        }
                    })
                    .then(json => {
                        self.noteFormWrapper.classList.remove('d-none');
                        self.relatedObjectField.value = id;
                        self.noteContainer.innerHTML = '';

                        for (let i = 0; i < json.notes.length; i++) {
                            let note = json.notes[i];
                            self.createNoteFromJson(note);
                        }
                    })
                })
            }
        })
    }

    createNoteFromJson(json) {
        if (json.notes) {
            json = json.notes[0]
        }
        let text = json.text;
        let timestamp = json.timestamp;
        let user = json.user;
        let card = document.createElement('div')
        card.classList.add('card', 'my-2')
        let cardBody = document.createElement('div')
        cardBody.classList.add('card-body', 'slim-tile')
    
        card.appendChild(cardBody)
    
        let p = document.createElement('p');
        p.classList.add('mb-0')
        p.innerHTML = `${timestamp} - ${user}<br/>${text}`;
        p.style.whiteSpace = 'normal';
        cardBody.appendChild(p)
        this.noteContainer.appendChild(card)
    
        this.noteContainer.scrollTop = this.noteContainer.scrollHeight;
    }
}
