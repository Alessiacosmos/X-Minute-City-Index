def adjust_map_saturation_figure(figure):
    figure.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        # Optional: Adds a subtle border around the plot area
        xaxis=dict(showgrid=True, showline=True, linecolor="lightgrey", mirror=True),
        yaxis=dict(showgrid=True, showline=True, linecolor="lightgrey", mirror=True),
    )

    figure.update_xaxes(showgrid=True, gridcolor="rgba(230, 230, 230, 0.8)")
    figure.update_yaxes(showgrid=True, gridcolor="rgba(230, 230, 230, 0.8)")

    return figure


adjust_figure_funcs = {"map_saturation": adjust_map_saturation_figure}
