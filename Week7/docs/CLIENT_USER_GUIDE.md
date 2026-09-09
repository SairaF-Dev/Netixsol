# Client User Guide

## Website

1. Choose Login or Register at `/start`. Registration asks for your name, phone,
   email, and a password of at least 10 characters.
2. Save your city, area, purpose, budget, property type, bedrooms, and amenities
   on Preferences. Specify whether the budget is for purchase or rent.
3. Browse Properties or load Recommendations. Like, reject, or shortlist shown
   recommendations to record feedback.
4. Open Sara at `/sara` and describe your requirements in English or UrduLish.
   Refer to a displayed result by its position, such as "second option".
5. Request a visit for a property and provide a date and time. Check the returned
   status and Appointments page before retrying a booking.

Saved preferences carry across sessions. Say "I want to change my preferences",
name a field such as budget, and provide its new value when asked. You can also
supply the field and replacement value together or use the Preferences page.

Visible text chat stays only while the page is open; navigation or reload starts
a new conversation. Saved preferences and recorded feedback remain on the server.
Development listings may be seed data; confirm real availability with the company.

## Voice

On `/sara`, sign in, choose **Start voice call**, and allow microphone access.
Use mute and end controls during the call. Browser voice needs localhost or
HTTPS and a configured voice service. Leaving the page ends the browser call.

For phone access, call the assigned VAPI number. Describe your buying, rental,
commercial, or investment requirement naturally. Give location, budget, property
type, and bedrooms progressively. Phone calls have a separate identity flow;
website login does not itself authenticate a telephone caller.

## Visits and help

Request a visit, reschedule an owned appointment, or cancel it. Workflow success
does not by itself establish email or Calendar delivery. If an error occurs after
submitting a visit, check the appointment list before retrying.

If results are unclear, provide an explicit city, area, and budget. Contact the
administrator with the time and visible error when failures repeat. Do not share
passwords, payment-card data, or unnecessary personal details.
