"""
Модуль аналитики цен с использованием Pandas и Plotly
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


def calculate_price_statistics(df: pd.DataFrame) -> Dict:
    if df.empty or 'price' not in df.columns:
        return {
            'count': 0,
            'mean': 0,
            'median': 0,
            'min': 0,
            'max': 0,
            'std': 0,
            'q25': 0,
            'q75': 0,
            'iqr': 0,
        }
    
    prices = df['price']
    
    return {
        'count': len(prices),
        'mean': float(prices.mean()),
        'median': float(prices.median()),
        'min': int(prices.min()),
        'max': int(prices.max()),
        'std': float(prices.std()),
        'q25': float(prices.quantile(0.25)),
        'q75': float(prices.quantile(0.75)),
        'iqr': float(prices.quantile(0.75) - prices.quantile(0.25)),
    }


def create_price_distribution_chart(df: pd.DataFrame, title: str = "Распределение цен") -> str:
    if df.empty or 'price' not in df.columns:
        return ""
    
    n_bins = min(30, max(10, int(np.sqrt(len(df)))))
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=df['price'],
        nbinsx=n_bins,
        name='Количество объявлений',
        marker_color='#8b5a3c',
        opacity=0.7,
        hovertemplate='Цена: %{x:,.0f} ₽<br>Количество: %{y}<extra></extra>',
    ))
    
    stats = calculate_price_statistics(df)
    if stats['mean'] > 0:
        fig.add_vline(
            x=stats['mean'],
            line_dash="dash",
            line_color="#6d4530",
            annotation_text=f"Средняя: {stats['mean']:,.0f} ₽",
            annotation_position="top"
        )
        fig.add_vline(
            x=stats['median'],
            line_dash="dot",
            line_color="#a67c52",
            annotation_text=f"Медиана: {stats['median']:,.0f} ₽",
            annotation_position="top"
        )
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#3d2817'}
        },
        xaxis_title="Цена, ₽",
        yaxis_title="Количество объявлений",
        template='plotly_white',
        plot_bgcolor='#faf8f5',
        paper_bgcolor='#ffffff',
        font=dict(family="Arial, sans-serif", size=12, color="#3d2817"),
        hovermode='closest',
        height=400,
    )
    
    fig.update_xaxes(
        tickformat=',.0f',
        gridcolor='#e8ddd4',
    )
    
    fig.update_yaxes(
        gridcolor='#e8ddd4',
    )
    
    return plot(fig, output_type='div', include_plotlyjs='cdn')


def create_price_timeline_chart(df: pd.DataFrame, title: str = "Динамика цен") -> str:
    if df.empty:
        return ""
    
    # Определяем колонку с датой
    date_col = None
    for col in ['checked_at', 'fetched_at', 'posted_date']:
        if col in df.columns:
            date_col = col
            break
    
    if not date_col:
        return ""
    
    timeline_df = df.copy()
    timeline_df[date_col] = pd.to_datetime(timeline_df[date_col])
    timeline_df = timeline_df.sort_values(date_col)
    
    timeline_df['date'] = timeline_df[date_col].dt.date
    daily_stats = timeline_df.groupby('date').agg({
        'price': ['mean', 'min', 'max', 'count']
    }).reset_index()
    
    daily_stats.columns = ['date', 'mean_price', 'min_price', 'max_price', 'count']
    daily_stats = daily_stats.sort_values('date')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['mean_price'],
        mode='lines+markers',
        name='Средняя цена',
        line=dict(color='#8b5a3c', width=3),
        marker=dict(size=6, color='#8b5a3c'),
        hovertemplate='Дата: %{x}<br>Средняя цена: %{y:,.0f} ₽<extra></extra>',
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['min_price'],
        mode='lines',
        name='Минимальная',
        line=dict(color='#10b981', width=2, dash='dash'),
        hovertemplate='Дата: %{x}<br>Мин. цена: %{y:,.0f} ₽<extra></extra>',
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['max_price'],
        mode='lines',
        name='Максимальная',
        line=dict(color='#ef4444', width=2, dash='dash'),
        hovertemplate='Дата: %{x}<br>Макс. цена: %{y:,.0f} ₽<extra></extra>',
    ))
    
    fig.add_trace(go.Scatter(
        x=list(daily_stats['date']) + list(daily_stats['date'])[::-1],
        y=list(daily_stats['max_price']) + list(daily_stats['min_price'])[::-1],
        fill='toself',
        fillcolor='rgba(139, 90, 60, 0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        showlegend=False,
    ))
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#3d2817'}
        },
        xaxis_title="Дата",
        yaxis_title="Цена, ₽",
        template='plotly_white',
        plot_bgcolor='#faf8f5',
        paper_bgcolor='#ffffff',
        font=dict(family="Arial, sans-serif", size=12, color="#3d2817"),
        hovermode='x unified',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    fig.update_xaxes(
        gridcolor='#e8ddd4',
    )
    
    fig.update_yaxes(
        tickformat=',.0f',
        gridcolor='#e8ddd4',
    )
    
    return plot(fig, output_type='div', include_plotlyjs='cdn')




def predict_price_trend(df: pd.DataFrame, days: int = 30) -> Dict:
    if df.empty or len(df) < 3:
        return {
            'trend': 'stable',
            'predicted_price': None,
            'confidence': 0,
        }
    
    date_col = None
    for col in ['checked_at', 'fetched_at', 'posted_date']:
        if col in df.columns:
            date_col = col
            break
    
    if not date_col:
        return {
            'trend': 'stable',
            'predicted_price': None,
            'confidence': 0,
        }
    
    timeline_df = df.copy()
    timeline_df[date_col] = pd.to_datetime(timeline_df[date_col])
    timeline_df = timeline_df.sort_values(date_col)
    timeline_df['date'] = timeline_df[date_col].dt.date
    
    daily_stats = timeline_df.groupby('date')['price'].mean().reset_index()
    daily_stats = daily_stats.sort_values('date')
    
    if len(daily_stats) < 3:
        return {
            'trend': 'stable',
            'predicted_price': float(daily_stats['price'].iloc[-1]) if len(daily_stats) > 0 else None,
            'confidence': 0,
        }
    
    daily_stats['days'] = (daily_stats['date'] - daily_stats['date'].min()).dt.days
    X = daily_stats['days'].values.reshape(-1, 1)
    y = daily_stats['price'].values
    
    n = len(X)
    X_mean = X.mean()
    y_mean = y.mean()
    
    numerator = ((X.flatten() - X_mean) * (y - y_mean)).sum()
    denominator = ((X.flatten() - X_mean) ** 2).sum()
    
    if denominator == 0:
        slope = 0
        intercept = y_mean
    else:
        slope = numerator / denominator
        intercept = y_mean - slope * X_mean
    
    def predict(x):
        return slope * x + intercept
    
    last_day = daily_stats['days'].max()
    future_day = last_day + days
    predicted_price = predict(future_day)
    
    if slope > 0:
        trend = 'up'
    elif slope < 0:
        trend = 'down'
    else:
        trend = 'stable'
    
    confidence = min(100, max(0, len(daily_stats) * 10))
    
    return {
        'trend': trend,
        'predicted_price': float(predicted_price),
        'current_price': float(daily_stats['price'].iloc[-1]),
        'confidence': int(confidence),
        'slope': float(slope),
    }
