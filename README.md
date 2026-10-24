# WayPointAI
This AI application uses job postings and successful resumes for roles the user is interested in and provides a roadmap of what the user can do to make themselves a more competitive applicant.

## Run the web interface

The interface accepts PDF or UTF-8 text resumes and target job titles, then runs
a resume-focused model locally. The model weights are downloaded from Hugging
Face the first time you request advice and cached for later runs. Resume text
stays on your computer.

The local model defaults to `AnusmitaRC21/smolified-resume-analyzer`, a
resume-focused 270M-parameter Gemma 3 model. You do not need a Hugging Face or
provider API key to download this public model. The first analysis requires an
internet connection and enough disk space for the model cache; later analyses
run locally.

Install dependencies and start the app:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The app analyzes up to 18,000 characters of extracted resume text per request.
Scanned PDFs without selectable text are not supported.
