async function uploadResume(){

    let fileInput = document.getElementById("resumeFile")

    let formData = new FormData()
    formData.append("file", fileInput.files[0])

    let response = await fetch("http://localhost:8000/upload_and_match",{
        method:"POST",
        body:formData
    })

    let data = await response.json()

    displayResults(data)
}

function displayResults(data){

    let resultsDiv = document.getElementById("results")
    resultsDiv.innerHTML=""

    data.top_matches.forEach(job =>{

        let div = document.createElement("div")
        div.className="job"

        div.innerHTML=`
        <h3>${job.job_title}</h3>
        <p><b>Company:</b> ${job.company}</p>
        <p><b>Match Score:</b> ${job.score}%</p>
        <p><b>Skills:</b> ${job.matched_skills.join(", ")}</p>
        `

        resultsDiv.appendChild(div)

    })
}