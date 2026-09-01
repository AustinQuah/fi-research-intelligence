import os

from nicegui import ui


APP_TITLE = 'FI Research Intelligence'


def index() -> None:
    with ui.header().classes(
        'bg-primary items-center px-6 py-3'
    ):
        ui.icon('hub', size='2rem')

        with ui.column().classes('gap-0'):
            ui.label(APP_TITLE).classes(
                'text-xl font-bold'
            )

            ui.label(
                'Proposal Research • Awards • Evidence'
            ).classes(
                'text-xs text-blue-100'
            )

    with ui.column().classes(
        'w-full max-w-6xl mx-auto p-6 gap-6'
    ):
        ui.label(
            'Welcome to FI Research Intelligence'
        ).classes(
            'text-3xl font-bold'
        )

        ui.label(
            'Your research workspace is online.'
        ).classes(
            'text-lg text-grey-7'
        )

        with ui.grid(columns=4).classes(
            'w-full gap-4'
        ):

            for title, icon, colour in [
                ('Proposals', 'description', 'primary'),
                ('Awards', 'workspace_premium', 'warning'),
                ('Research', 'science', 'positive'),
                ('Review', 'fact_check', 'secondary'),
            ]:

                with ui.card().classes(
                    'w-full p-5'
                ):

                    with ui.row().classes(
                        'items-center justify-between'
                    ):
                        ui.label(title).classes(
                            'text-lg font-bold'
                        )

                        ui.icon(
                            icon,
                            color=colour,
                            size='1.7rem',
                        )

                    ui.label(
                        'Ready'
                    ).classes(
                        'text-grey-6'
                    )

        with ui.card().classes(
            'w-full p-6'
        ):
            ui.label(
                'Deployment test'
            ).classes(
                'text-xl font-bold'
            )

            ui.label(
                'If you can see this page, '
                'Render + NiceGUI are working correctly.'
            ).classes(
                'text-grey-7'
            )

            ui.button(
                'Test interaction',
                on_click=lambda:
                    ui.notify(
                        'NiceGUI is working!',
                        type='positive',
                    ),
            ).props(
                'color=primary'
            )


ui.run(
    root=index,
    host='0.0.0.0',
    port=int(
        os.environ.get(
            'PORT',
            '10000',
        )
    ),
    title=APP_TITLE,
    favicon='🔬',
    reload=False,
)
