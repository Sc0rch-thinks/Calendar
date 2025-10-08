from argparse import ArgumentParser, Namespace
import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # pyright: ignore[reportMissingTypeStubs]
from googleapiclient.discovery import build  # pyright: ignore[reportUnknownVariableType]
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def sign_in() -> Credentials:
    """Sign the user to the Google Calendar API."""
    creds: Credentials | None = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)  # pyright: ignore[reportUnknownMemberType]

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def calendars(creds: Credentials, args: Namespace) -> None:
    """prints the calendar ids that is linked to this user"""
    service = build("calendar", "v3", credentials=creds)
    calendar_list = service.calendarList().list().execute()

    if args.verbose:
        print(f"Found {len(calendar_list['items'])} calendar(s)\n")

    for calendar in calendar_list["items"]:
        calendar_id = calendar.get("id", "")
        summary = calendar.get("summary", "")
        print("_" * 80)
        print(f"👨{summary}\n🗓️{calendar_id}")

    print("_" * 80)


def events(creds: Credentials, args: Namespace) -> None:
    """Prints the events in the specified calendar."""
    try:
        service = build("calendar", "v3", credentials=creds)

        # Determine the start time based on args
        if args.date:
            # Parse the date string (expecting format like YYYY-MM-DD)
            start_date = datetime.datetime.fromisoformat(args.date)
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=datetime.timezone.utc)
        else:
            start_date = datetime.datetime.now(tz=datetime.timezone.utc)

        # Calculate end time based on timeout
        end_date = start_date + datetime.timedelta(days=args.timeout)

        time_min = start_date.isoformat()
        time_max = end_date.isoformat()

        calendar_id = args.calendar
        max_results = args.number

        if args.verbose:
            print(f"Fetching {max_results} events from calendar '{calendar_id}'")
            print(f"Time range: {time_min} to {time_max}")

        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # for event in events:
        #     from pprint import pprint
        #     pprint(event)

        # return

        # Prints the start, end, and name of the events
        for event in events:
            date = event["start"].get("date")
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            summary = event.get("summary", "(No title)")

            if date == None:
                start_dt = datetime.datetime.fromisoformat(start)
                end_dt = datetime.datetime.fromisoformat(end)
                date = start_dt.date()
                print("_" * 80)
                print(f"📅Date: {date}")
                print(
                    f"⏰Time: {start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
                )
                print(f"📝Summary: {summary}")
                
                continue

            print("_" * 80)
            print(f"📅Date: {date}")
            print(f"⏰All Day Event")
            print(f"📝Summary: {summary}")

        print("_" * 80)
        print(f"\nTotal events: {len(events)}")

    except HttpError as error:
        print(f"An error occurred: {error}")


def new_event(creds: Credentials, args: Namespace) -> None:
    """Create a new event in the user's calendar."""
    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = args.calendar

        # Parse start time (default to now if not provided)
        if args.start:
            start_time = datetime.datetime.fromisoformat(args.start)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=datetime.timezone.utc)
        else:
            start_time = datetime.datetime.now(tz=datetime.timezone.utc)

        # Parse end time (default to 1 hour after start if not provided)
        if args.end:
            end_time = datetime.datetime.fromisoformat(args.end)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=datetime.timezone.utc)
        else:
            end_time = start_time + datetime.timedelta(hours=1)

        # Build the event body
        event_body = {
            "summary": args.summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
        }

        # Add optional fields if provided
        if args.location:
            event_body["location"] = args.location

        if args.description:
            event_body["description"] = args.description

        if args.verbose:
            print(f"Creating event in calendar '{calendar_id}'")
            print(f"Summary: {args.summary}")
            print(f"Start: {start_time.isoformat()}")
            print(f"End: {end_time.isoformat()}")
            if args.location:
                print(f"Location: {args.location}")
            if args.description:
                print(f"Description: {args.description}")

        # Create the event
        event = (
            service.events().insert(calendarId=calendar_id, body=event_body).execute()
        )

        print("_" * 80)
        print("✅ Event created successfully!")
        print(f"📝 Summary: {event.get('summary')}")
        print(f"🆔 Event ID: {event.get('id')}")
        print(f"🔗 Link: {event.get('htmlLink')}")
        print("_" * 80)

    except ValueError as error:
        print(f"Error parsing date/time: {error}")
        print(
            "Please use ISO format (e.g., 2024-01-15T10:00:00 or 2024-01-15T10:00:00-05:00)"
        )
    except HttpError as error:
        print(f"An error occurred: {error}")


def main():
    """Command-line interface for Google Calendar API.

    This script provides a command-line interface for interacting with the Google Calendar API.
    It allows users to list events, create events, and manage calendars.
    """

    # Create the main parser
    parser = ArgumentParser(description="Google Calendar CLI Tool")

    # Global options
    parser.add_argument(
        "-v", "--version", action="version", version="calendar-cli 1.0.0"
    )
    parser.add_argument(
        "-c",
        "--calendar",
        default="primary",
        help="calendar ID to operate on (default: primary)",
    )
    parser.add_argument("--verbose", action="store_true", help="enable verbose output")
    parser.add_argument("--config", metavar="path", help="path to config file")

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="available commands")

    # calendars command
    parser_calendars = subparsers.add_parser(
        "calendars", help="List all calendar IDs linked to this user"
    )

    # events command
    parser_events = subparsers.add_parser(
        "events", help="List events from the calendar"
    )
    parser_events.add_argument(
        "-n",
        "--number",
        type=int,
        default=10,
        help="number of events to fetch (default: 10)",
    )
    parser_events.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=7,
        help="number of days to fetch (default: 7)",
    )
    parser_events.add_argument(
        "-d",
        "--date",
        help="date to start fetching from (default: today)",
    )

    # new command
    parser_new = subparsers.add_parser("new", help="Create a new event in the calendar")
    parser_new.add_argument(
        "-S", "--summary", required=True, help="event summary/title (required)"
    )
    parser_new.add_argument(
        "-s", "--start", help="start time in ISO format (default: now)"
    )
    parser_new.add_argument(
        "-e", "--end", help="end time in ISO format (default: 1 hour after start)"
    )
    parser_new.add_argument("-l", "--location", help="location for the event")
    parser_new.add_argument("-d", "--description", help="description for the event")

    # Parse arguments
    args = parser.parse_args()

    creds = sign_in()
    # Execute the appropriate command
    if args.command == "calendars":
        calendars(creds, args)
    elif args.command == "events":
        events(creds, args)
    elif args.command == "new":
        new_event(creds, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
