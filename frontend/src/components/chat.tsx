"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AgencyLog } from "@/components/agency-log";
import { Markdown } from "@/components/markdown";
import type { AgencyEntry, AgentEvent } from "@/lib/types";

type Status = "idle" | "working" | "done" | "aborted" | "error";

type GitlabUser = { username: string; name: string; avatar_url: string };
type Auth =
  | { state: "loading" }
  | { state: "out" }
  | { state: "in"; user: GitlabUser };

type Turn =
  | { role: "user"; id: string; text: string }
  | { role: "agent"; id: string; agency: AgencyEntry[]; text: string; status: Status };

const SUGGESTIONS = [
  "Check open issue #1 and identify the file responsible. Do not modify anything.",
  "Fix the syntax error described in issue #1 and open a Merge Request.",
];

export function LogoSVG({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      version="1.1"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      fill="currentColor"
      className={className}
    >
      <path d="M46.06 89.59 L47.31 89.59 L47.51 89.79 L52.28 89.79 L52.49 89.59 L54.56 89.59 L54.77 89.38 L56.01 89.38 L56.22 89.17 L57.25 89.17 L57.46 88.96 L58.29 88.96 L58.50 88.76 L58.91 88.76 L58.91 88.34 L58.70 88.13 L58.70 87.72 L58.50 87.51 L58.50 87.10 L58.29 86.89 L58.29 86.48 L58.08 86.27 L58.08 85.85 L57.88 85.65 L57.88 85.23 L57.67 85.03 L57.67 84.40 L57.46 84.20 L57.46 83.78 L57.25 83.58 L57.25 83.16 L57.05 82.95 L57.05 82.54 L56.84 82.33 L56.84 81.92 L56.63 81.71 L56.63 81.30 L56.42 81.09 L56.42 80.67 L56.22 80.47 L56.22 80.05 L56.01 79.84 L56.01 79.22 L55.80 79.02 L55.80 78.60 L55.60 78.39 L55.60 77.98 L55.39 77.77 L55.39 77.36 L55.18 77.15 L55.18 76.74 L54.97 76.53 L54.97 76.11 L54.77 75.91 L54.77 75.28 L54.56 75.08 L54.56 74.66 L54.35 74.46 L54.35 74.04 L54.15 73.83 L54.15 73.42 L53.94 73.21 L53.94 72.80 L53.73 72.59 L53.73 72.18 L53.52 71.97 L53.52 71.35 L53.32 71.14 L53.32 70.73 L53.11 70.52 L53.11 70.10 L52.90 69.90 L52.90 69.48 L52.69 69.27 L52.69 68.86 L52.49 68.65 L52.49 68.24 L52.28 68.03 L52.28 67.62 L52.07 67.41 L52.07 66.99 L51.87 66.79 L51.87 66.17 L51.66 65.96 L51.66 65.54 L51.45 65.34 L51.45 64.92 L51.24 64.72 L51.24 64.30 L51.04 64.09 L51.04 63.68 L50.83 63.47 L50.83 63.06 L50.62 62.85 L50.62 62.23 L50.41 62.02 L50.41 61.61 L50.21 61.40 L50.21 60.98 L50.00 60.78 L50.00 60.16 L50.21 59.95 L50.21 59.74 L51.04 58.91 L51.45 58.91 L51.66 58.70 L51.87 58.70 L52.07 58.91 L52.49 58.91 L53.52 59.95 L53.73 59.95 L56.63 62.85 L56.84 62.85 L61.81 67.62 L62.02 67.62 L64.30 69.90 L64.51 69.90 L67.20 72.59 L67.41 72.59 L69.90 75.08 L70.10 75.08 L72.59 77.56 L72.80 77.56 L75.49 80.26 L76.11 80.05 L80.05 76.11 L80.05 75.91 L80.88 75.08 L80.88 74.87 L82.33 73.21 L82.33 73.01 L83.58 71.35 L83.78 70.73 L83.58 70.73 L83.37 70.52 L82.75 70.31 L82.33 69.90 L82.12 69.90 L81.92 69.69 L81.71 69.69 L81.50 69.48 L81.30 69.48 L81.09 69.27 L80.88 69.27 L80.67 69.07 L80.47 69.07 L80.26 68.86 L78.81 68.24 L78.39 67.82 L78.19 67.82 L77.98 67.62 L77.77 67.62 L77.56 67.41 L77.36 67.41 L77.15 67.20 L76.94 67.20 L76.74 66.99 L75.28 66.37 L74.87 65.96 L74.66 65.96 L74.46 65.75 L74.25 65.75 L74.04 65.54 L73.83 65.54 L73.63 65.34 L73.42 65.34 L73.21 65.13 L71.76 64.51 L71.35 64.09 L71.14 64.09 L70.93 63.89 L70.73 63.89 L70.52 63.68 L70.31 63.68 L70.10 63.47 L69.90 63.47 L69.69 63.26 L68.24 62.64 L67.82 62.23 L67.62 62.23 L67.41 62.02 L67.20 62.02 L66.99 61.81 L66.79 61.81 L66.58 61.61 L66.37 61.61 L66.17 61.40 L65.96 61.40 L65.75 61.19 L64.30 60.57 L63.89 60.16 L63.68 60.16 L63.47 59.95 L63.26 59.95 L63.06 59.74 L62.85 59.74 L62.64 59.53 L61.19 58.91 L60.78 58.50 L60.57 58.50 L60.36 58.29 L60.16 58.29 L59.95 58.08 L59.74 58.08 L59.53 57.88 L59.33 57.88 L59.12 57.67 L58.91 57.67 L58.70 57.46 L57.25 56.84 L56.84 56.42 L56.63 56.42 L56.42 56.22 L56.22 56.22 L53.94 54.97 L53.32 54.97 L53.11 54.77 L50.83 54.77 L50.62 54.97 L50.00 54.97 L49.79 55.18 L48.76 55.60 L48.34 56.01 L48.13 56.01 L47.31 56.84 L47.31 57.05 L46.48 58.08 L46.48 58.50 L46.27 58.70 L46.27 59.12 L46.06 59.33 Z" />
      <path d="M10.21 46.06 L10.21 47.51 L10.00 47.72 L10.00 52.07 L10.21 52.28 L10.21 54.35 L10.41 54.56 L10.41 56.01 L10.62 56.22 L10.62 57.25 L10.83 57.46 L10.83 58.29 L11.04 58.50 L11.04 58.91 L11.24 59.12 L11.45 58.91 L11.87 58.91 L12.07 58.70 L12.49 58.70 L12.69 58.50 L13.11 58.50 L13.32 58.29 L13.73 58.29 L13.94 58.08 L14.35 58.08 L14.56 57.88 L14.97 57.88 L15.18 57.67 L15.80 57.67 L16.01 57.46 L16.42 57.46 L16.63 57.25 L17.05 57.25 L17.25 57.05 L17.67 57.05 L17.88 56.84 L18.29 56.84 L18.50 56.63 L18.91 56.63 L19.12 56.42 L19.53 56.42 L19.74 56.22 L20.36 56.22 L20.57 56.01 L20.98 56.01 L21.19 55.80 L21.61 55.80 L21.81 55.60 L22.23 55.60 L22.44 55.39 L22.85 55.39 L23.06 55.18 L23.47 55.18 L23.68 54.97 L24.09 54.97 L24.30 54.77 L24.92 54.77 L25.13 54.56 L25.54 54.56 L25.75 54.35 L26.17 54.35 L26.37 54.15 L26.79 54.15 L26.99 53.94 L27.41 53.94 L27.62 53.73 L28.24 53.73 L28.86 53.32 L29.48 53.32 L29.69 53.11 L30.10 53.11 L30.31 52.90 L30.73 52.90 L30.93 52.69 L31.35 52.69 L31.55 52.49 L31.97 52.49 L32.18 52.28 L32.80 52.28 L33.01 52.07 L33.42 52.07 L33.63 51.87 L34.04 51.87 L34.25 51.66 L34.66 51.66 L34.87 51.45 L35.28 51.45 L35.49 51.24 L35.91 51.24 L36.11 51.04 L36.53 51.04 L36.74 50.83 L37.36 50.83 L37.56 50.62 L37.98 50.62 L38.19 50.41 L38.60 50.41 L38.81 50.21 L39.84 50.21 L40.67 50.83 L40.67 51.04 L41.09 51.66 L40.88 52.69 L39.22 54.35 L39.22 54.56 L36.74 57.05 L36.74 57.25 L34.04 59.95 L34.04 60.16 L31.55 62.64 L31.55 62.85 L29.07 65.34 L29.07 65.54 L26.79 67.82 L26.79 68.03 L26.58 68.24 L26.37 68.24 L26.37 68.45 L24.30 70.52 L24.30 70.73 L21.40 73.63 L21.40 73.83 L19.53 75.70 L19.74 75.91 L19.74 76.11 L23.68 80.05 L23.89 80.05 L24.92 81.09 L25.13 81.09 L26.58 82.33 L26.79 82.33 L28.45 83.58 L29.07 83.78 L29.27 83.58 L29.90 82.12 L30.31 81.71 L30.31 81.50 L30.52 81.30 L30.52 81.09 L30.73 80.88 L30.73 80.67 L30.93 80.47 L31.55 79.02 L31.97 78.60 L31.97 78.39 L32.18 78.19 L32.18 77.98 L32.38 77.77 L32.38 77.56 L32.59 77.36 L32.59 77.15 L32.80 76.94 L32.80 76.74 L33.01 76.53 L33.63 75.08 L34.04 74.66 L34.04 74.46 L34.25 74.25 L34.25 74.04 L34.46 73.83 L34.46 73.63 L34.66 73.42 L34.66 73.21 L34.87 73.01 L35.49 71.55 L35.91 71.14 L35.91 70.93 L36.11 70.73 L36.11 70.52 L36.32 70.31 L36.32 70.10 L36.53 69.90 L37.15 68.45 L37.56 68.03 L37.56 67.62 L37.98 67.20 L37.98 66.99 L38.19 66.79 L38.19 66.58 L38.39 66.37 L38.39 66.17 L38.60 65.96 L39.22 64.51 L39.64 64.09 L39.64 63.89 L39.84 63.68 L39.84 63.47 L40.05 63.26 L40.05 63.06 L40.26 62.85 L40.26 62.64 L40.47 62.44 L40.47 62.23 L40.67 62.02 L41.30 60.57 L41.71 60.16 L41.71 59.95 L41.92 59.74 L41.92 59.53 L42.12 59.33 L42.12 59.12 L42.33 58.91 L42.95 57.46 L43.37 57.05 L43.37 56.84 L43.58 56.63 L43.58 56.42 L44.82 54.15 L44.82 53.52 L45.03 53.32 L45.03 50.83 L44.82 50.62 L44.61 49.59 L43.99 48.76 L43.99 48.55 L42.54 47.10 L42.33 47.10 L41.92 46.68 L41.50 46.68 L41.30 46.48 L40.88 46.48 L40.67 46.27 L40.05 46.27 L39.84 46.06 Z" />
         <path d="M70.73 16.01 L70.10 16.84 L70.10 17.05 L69.90 17.25 L69.90 17.46 L69.69 17.67 L69.69 17.88 L69.48 18.08 L69.48 18.29 L69.27 18.50 L68.65 19.95 L68.24 20.36 L68.24 20.57 L68.03 20.78 L68.03 20.98 L67.82 21.19 L67.82 21.40 L67.62 21.61 L67.62 21.81 L67.41 22.02 L67.41 22.23 L67.20 22.44 L66.58 23.89 L66.17 24.30 L66.17 24.51 L65.96 24.72 L65.96 24.92 L65.75 25.13 L65.75 25.34 L65.54 25.54 L64.92 26.99 L64.51 27.41 L64.51 27.62 L64.30 27.82 L64.30 28.03 L64.09 28.24 L64.09 28.45 L63.89 28.65 L63.89 28.86 L63.68 29.07 L63.68 29.27 L63.47 29.48 L62.85 30.93 L62.44 31.35 L62.44 31.55 L62.23 31.76 L62.23 31.97 L62.02 32.18 L62.02 32.38 L61.81 32.59 L61.81 32.80 L61.61 33.01 L60.98 34.46 L60.57 34.87 L60.57 35.08 L60.36 35.28 L60.36 35.49 L60.16 35.70 L60.16 35.91 L59.95 36.11 L59.95 36.32 L59.74 36.53 L59.12 37.98 L58.70 38.39 L58.70 38.60 L58.50 38.81 L58.50 39.02 L58.29 39.22 L58.29 39.43 L58.08 39.64 L57.46 41.09 L57.05 41.50 L57.05 41.71 L56.84 41.92 L56.84 42.12 L56.63 42.33 L56.63 42.54 L56.42 42.75 L56.42 42.95 L56.22 43.16 L56.22 43.37 L54.97 45.65 L54.97 46.06 L54.77 46.27 L54.77 46.89 L54.56 47.10 L54.56 48.55 L54.77 48.76 L54.77 49.59 L54.97 49.79 L54.97 50.21 L55.60 51.04 L55.60 51.24 L56.63 52.49 L56.84 52.49 L57.88 53.32 L58.29 53.32 L58.50 53.52 L58.91 53.52 L59.12 53.73 L60.36 53.73 L60.57 53.94 L68.03 53.94 L68.24 53.73 L89.59 53.73 L89.59 52.07 L89.79 51.87 L89.79 47.93 L89.59 47.72 L89.59 45.44 L89.38 45.23 L89.38 43.99 L89.17 43.78 L89.17 42.75 L88.96 42.54 L88.96 41.71 L88.76 41.50 L88.76 40.88 L88.34 40.88 L88.13 41.09 L87.72 41.09 L87.51 41.30 L87.10 41.30 L86.89 41.50 L86.48 41.50 L86.27 41.71 L85.65 41.71 L85.03 42.12 L84.40 42.12 L84.20 42.33 L83.78 42.33 L83.58 42.54 L83.16 42.54 L82.95 42.75 L82.54 42.75 L82.33 42.95 L81.92 42.95 L81.71 43.16 L81.09 43.16 L80.88 43.37 L80.47 43.37 L80.26 43.58 L79.84 43.58 L79.64 43.78 L79.22 43.78 L79.02 43.99 L78.60 43.99 L78.39 44.20 L77.98 44.20 L77.77 44.40 L77.36 44.40 L77.15 44.61 L76.53 44.61 L75.91 45.03 L75.28 45.03 L75.08 45.23 L74.66 45.23 L74.46 45.44 L74.04 45.44 L73.83 45.65 L73.42 45.65 L73.21 45.85 L72.80 45.85 L72.59 46.06 L71.97 46.06 L71.76 46.27 L71.35 46.27 L71.14 46.48 L70.73 46.48 L70.52 46.68 L70.10 46.68 L69.90 46.89 L69.48 46.89 L69.27 47.10 L68.86 47.10 L68.65 47.31 L68.24 47.31 L68.03 47.51 L67.41 47.51 L67.20 47.72 L66.79 47.72 L66.58 47.93 L66.17 47.93 L65.96 48.13 L65.96 48.13 L65.34 48.34 L64.92 48.34 L64.72 48.55 L64.30 48.55 L64.09 48.76 L63.68 48.76 L63.47 48.96 L62.85 48.96 L62.64 49.17 L62.23 49.17 L62.02 49.38 L61.61 49.38 L61.40 49.59 L60.98 49.59 L60.78 49.79 L59.95 49.79 L59.74 49.59 L59.53 49.59 L58.91 48.96 L58.91 48.76 L58.70 48.55 L58.70 47.51 L58.91 47.31 L58.91 47.10 L61.19 44.82 L61.19 44.61 L63.68 42.12 L63.68 41.92 L65.96 39.64 L65.96 39.43 L68.65 36.74 L68.65 36.53 L70.93 34.25 L70.93 34.04 L71.14 33.83 L71.35 33.83 L71.35 33.63 L73.42 31.55 L73.42 31.35 L75.91 28.86 L75.91 28.65 L78.81 25.75 L78.81 25.54 L80.26 24.09 L79.84 23.68 L79.84 23.47 L76.32 19.95 L76.11 19.95 L75.08 18.91 L74.87 18.91 L73.21 17.46 L73.01 17.46 L71.35 16.22 Z" />
          <path d="M53.73 10.21 L52.07 10.21 L51.87 10.00 L47.93 10.00 L47.72 10.21 L45.44 10.21 L45.23 10.41 L43.99 10.41 L43.78 10.62 L42.75 10.62 L42.54 10.83 L41.71 10.83 L41.50 11.04 L40.88 11.04 L40.67 11.24 L40.88 11.45 L40.88 11.87 L41.09 12.07 L41.09 12.49 L41.30 12.69 L41.30 13.11 L41.50 13.32 L41.50 13.73 L41.71 13.94 L41.71 14.56 L41.92 14.77 L41.92 15.18 L42.12 15.39 L42.12 15.80 L42.33 16.01 L42.33 16.42 L42.54 16.63 L42.54 17.05 L42.75 17.25 L42.75 17.67 L42.95 17.88 L42.95 18.50 L43.16 18.70 L43.16 19.12 L43.37 19.33 L43.37 19.74 L43.58 19.95 L43.58 20.36 L43.78 20.57 L43.78 20.98 L43.99 21.19 L43.99 21.61 L44.20 21.81 L44.20 22.23 L44.40 22.44 L44.40 22.85 L44.61 23.06 L44.61 23.68 L44.82 23.89 L44.82 24.30 L45.03 24.51 L45.03 24.92 L45.23 25.13 L45.23 25.54 L45.44 25.75 L45.44 26.17 L45.65 26.37 L45.65 26.79 L45.85 26.99 L45.85 27.62 L46.06 27.82 L46.06 28.24 L46.27 28.45 L46.27 28.86 L46.48 29.07 L46.48 29.48 L46.68 29.69 L46.68 30.10 L46.89 30.31 L46.89 30.73 L47.10 30.93 L47.10 31.35 L47.31 31.55 L47.31 31.97 L47.51 32.18 L47.51 32.80 L47.72 33.01 L47.72 33.42 L47.93 33.63 L47.93 34.04 L48.13 34.25 L48.13 34.66 L48.34 34.87 L48.34 35.28 L48.55 35.49 L48.55 36.11 L48.96 36.74 L48.96 37.36 L49.17 37.56 L49.17 37.98 L49.38 38.19 L49.38 38.60 L49.59 38.81 L49.59 40.05 L49.38 40.26 L49.38 40.47 L48.55 41.09 L47.31 41.09 L46.89 40.67 L46.68 40.67 L43.99 37.98 L43.78 37.98 L41.30 35.49 L41.09 35.49 L35.91 30.52 L35.70 30.52 L33.21 28.03 L33.01 28.03 L30.52 25.54 L30.31 25.54 L27.82 23.06 L27.62 23.06 L24.72 20.16 L24.51 20.16 L24.09 19.74 L23.47 19.95 L19.74 23.68 L19.74 23.89 L18.91 24.72 L18.91 24.92 L17.46 26.58 L17.46 26.79 L16.22 28.45 L16.22 28.65 L16.01 28.86 L16.01 29.27 L17.05 29.69 L17.46 30.10 L17.67 30.10 L17.88 30.31 L18.08 30.31 L18.29 30.52 L18.50 30.52 L18.70 30.73 L18.91 30.73 L19.12 30.93 L20.57 31.55 L20.98 31.97 L21.19 31.97 L21.40 32.18 L21.61 32.18 L21.81 32.38 L22.02 32.38 L22.23 32.59 L22.44 32.59 L22.64 32.80 L24.09 33.42 L24.51 33.83 L24.72 33.83 L24.92 34.04 L25.13 34.04 L25.34 34.25 L25.54 34.25 L25.75 34.46 L25.96 34.46 L26.17 34.66 L27.62 35.28 L28.03 35.70 L28.24 35.70 L28.45 35.91 L28.65 35.91 L28.86 36.11 L29.07 36.11 L29.27 36.32 L29.48 36.32 L29.69 36.53 L31.14 37.15 L31.55 37.56 L31.76 37.56 L31.97 37.77 L32.18 37.77 L32.38 37.98 L32.59 37.98 L32.80 38.19 L33.01 38.19 L33.21 38.39 L34.66 39.02 L35.08 39.43 L35.28 39.43 L35.49 39.64 L35.70 39.64 L35.91 39.84 L36.11 39.84 L36.32 40.05 L36.53 40.05 L36.74 40.26 L38.19 40.88 L38.60 41.30 L38.81 41.30 L39.02 41.50 L39.22 41.50 L39.43 41.71 L39.64 41.71 L39.84 41.92 L40.05 41.92 L40.26 42.12 L40.47 42.12 L40.67 42.33 L42.12 42.95 L42.54 43.37 L42.75 43.37 L42.95 43.58 L43.16 43.58 L43.37 43.78 L43.58 43.78 L45.85 45.03 L46.48 45.03 L46.68 45.23 L48.55 45.23 L48.76 45.03 L49.38 45.03 L49.59 44.82 L50.00 44.82 L50.21 44.61 L51.24 44.20 L52.49 42.95 L52.49 42.75 L52.90 42.33 L52.90 42.12 L53.52 41.09 L53.52 40.47 L53.73 40.26 Z" />
    </svg>
  );
}

function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col gap-6 border-r border-[var(--color-border)] bg-[var(--color-bg)] p-4 md:flex overflow-y-auto">
      <div className="flex flex-col">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-faint)]">
          Telemetry
        </div>
        <ul className="flex flex-col gap-1 list-none">
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span className="flex items-center gap-1.5">
              <svg className="h-3.5 w-3.5 text-[var(--color-faint)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Vertex AI
            </span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">Active</span>
          </li>
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span className="flex items-center gap-1.5">
              <svg className="h-3.5 w-3.5 text-[var(--color-faint)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Secret Manager
            </span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">Mounted</span>
          </li>
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span className="flex items-center gap-1.5">
              <svg className="h-3.5 w-3.5 text-[var(--color-faint)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Cloud Build
            </span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">Ready</span>
          </li>
        </ul>
      </div>

      <div className="flex flex-col">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-faint)]">
          Safety Rules
        </div>
        <ul className="flex flex-col gap-1 list-none">
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span>Main Commits</span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">Blocked</span>
          </li>
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span>Branch Enforcer</span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">sentinel/*</span>
          </li>
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span>Destructive Tools</span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">Disabled</span>
          </li>
        </ul>
      </div>

      <div className="flex flex-col">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-faint)]">
          Parameters
        </div>
        <ul className="flex flex-col gap-1 list-none">
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span>Model</span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">gemini-3.5-flash</span>
          </li>
          <li className="flex items-center justify-between rounded border border-transparent px-2 py-1.5 text-xs text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface-2)]">
            <span>Max Steps</span>
            <span className="rounded border border-[var(--color-border)] bg-[var(--color-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text)]">10</span>
          </li>
        </ul>
      </div>
    </aside>
  );
}

export function Chat() {
  const [auth, setAuth] = useState<Auth>({ state: "loading" });
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [gitlabProject, setGitlabProject] = useState<string>("");
  const [inputProject, setInputProject] = useState<string>("");
  const [projectCheck, setProjectCheck] = useState<"idle" | "checking" | "valid" | "invalid">("idle");
  const [projectError, setProjectError] = useState<string>("");

  useEffect(() => {
    // sessionStorage is client-only; seed state post-mount to avoid an SSR hydration mismatch.
    const saved = sessionStorage.getItem("gitlab_project") || "";
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setGitlabProject(saved);
    setInputProject(saved);
    if (saved) setProjectCheck("valid");
  }, []);

  // Resolve auth state on mount: ask our own /api/auth/me (reads the httpOnly cookie).
  useEffect(() => {
    let alive = true;
    fetch("/api/auth/me")
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((d: { user: GitlabUser }) => alive && setAuth({ state: "in", user: d.user }))
      .catch(() => alive && setAuth({ state: "out" }));
    return () => {
      alive = false;
    };
  }, []);

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    setAuth({ state: "out" });
  }, []);

  // Auto-scroll logic to keep latest content in view
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns]);

  const send = useCallback(
    async (prompt: string) => {
      const text = prompt.trim();
      if (!text || busy) return;

      const userTurn: Turn = { role: "user", id: crypto.randomUUID(), text };
      const agentId = crypto.randomUUID();
      const agentTurn: Turn = {
        role: "agent",
        id: agentId,
        agency: [],
        text: "",
        status: "working",
      };
      setTurns((prev) => [...prev, userTurn, agentTurn]);
      setInput("");
      setBusy(true);

      const patch = (fn: (t: Extract<Turn, { role: "agent" }>) => void) =>
        setTurns((prev) =>
          prev.map((t) => {
            if (t.id !== agentId || t.role !== "agent") return t;
            const next = { ...t, agency: [...t.agency] };
            fn(next);
            return next;
          }),
        );

      try {
        const res = await fetch("/api/agent/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: text,
            session_id: "ui",
            gitlab_project: gitlabProject || undefined,
          }),
        });
        if (!res.body) throw new Error("no stream");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const line = frame.split("\n").find((l) => l.startsWith("data:"));
            if (!line) continue;
            const event = JSON.parse(line.slice(5).trim()) as AgentEvent;
            applyEvent(event, patch);
          }
        }
      } catch {
        patch((t) => {
          t.status = "error";
          t.agency.push({ kind: "status", text: "Connection failed.", tone: "danger" });
        });
      } finally {
        setBusy(false);
      }
    },
    [busy],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  };

  if (auth.state !== "in") {
    return <LoginGate loading={auth.state === "loading"} />;
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[var(--color-bg)]">
      <Header user={auth.user} onLogout={logout} />

      {/* Target Project Config Bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-[var(--color-border)] px-6 py-3 bg-[var(--color-surface)] text-xs">
        <div className="flex items-center gap-4">
          <span className="text-[var(--color-faint)] font-mono text-[10px] uppercase tracking-wider shrink-0">Target Repo:</span>
          <div className="flex items-center rounded border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 focus-within:border-[var(--color-text)] transition-colors">
            <input
              type="text"
              value={inputProject}
              onChange={(e) => {
                setInputProject(e.target.value);
                if (projectCheck !== "idle") setProjectCheck("idle");
              }}
              placeholder="namespace/project-name"
              className="w-72 bg-transparent font-mono text-[11px] leading-normal text-[var(--color-text)] placeholder:text-[var(--color-faint)] focus:outline-none focus:ring-0 border-none outline-none"
            />
          </div>
          <button
            type="button"
            disabled={projectCheck === "checking"}
            onClick={async () => {
              const val = inputProject.trim();
              if (!val) {
                setGitlabProject("");
                setProjectCheck("idle");
                setProjectError("");
                sessionStorage.removeItem("gitlab_project");
                return;
              }
              setProjectCheck("checking");
              setProjectError("");
              try {
                const res = await fetch(`/api/gitlab/project?path=${encodeURIComponent(val)}`);
                const data = await res.json() as { ok: boolean; reason?: string; name?: string };
                if (data.ok) {
                  setGitlabProject(val);
                  setProjectCheck("valid");
                  sessionStorage.setItem("gitlab_project", val);
                } else {
                  setGitlabProject("");
                  setProjectCheck("invalid");
                  setProjectError(data.reason === "not_found" ? "Project not found" : data.reason === "unauthorized" ? "Access denied" : "Could not reach GitLab");
                  sessionStorage.removeItem("gitlab_project");
                }
              } catch {
                setGitlabProject("");
                setProjectCheck("invalid");
                setProjectError("Could not reach GitLab");
                sessionStorage.removeItem("gitlab_project");
              }
            }}
            className="rounded bg-[var(--color-text)] px-3 py-1.5 text-[10px] font-semibold text-[var(--color-bg)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] border border-[var(--color-text)] transition-colors shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {projectCheck === "checking" ? "Checking…" : "Set"}
          </button>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[var(--color-muted)]">
          <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${
            projectCheck === "valid" ? "bg-white" :
            projectCheck === "checking" ? "bg-[var(--color-faint)] pulse-indicator" :
            "bg-[var(--color-faint)]"
          }`}></span>
          {projectCheck === "invalid"
            ? <span className="text-[var(--color-muted)]">{projectError}</span>
            : <span>Active: <strong className="text-[var(--color-text)]">{gitlabProject || "Server Default"}</strong></span>
          }
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex flex-1 flex-col overflow-hidden relative">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-8">
            <div className="mx-auto w-full max-w-2xl">
              {turns.length === 0 ? (
                <EmptyState onPick={(s) => void send(s)} disabled={busy} />
              ) : (
                <div className="flex flex-col gap-6">
                  {turns.map((turn) =>
                    turn.role === "user" ? (
                      <UserMessage key={turn.id} text={turn.text} />
                    ) : (
                      <AgentMessage key={turn.id} turn={turn} />
                    ),
                  )}
                </div>
              )}
            </div>
          </div>

          <footer className="border-t border-[var(--color-border)] bg-[var(--color-bg)] py-4 shrink-0">
            <form onSubmit={onSubmit} className="mx-auto w-full max-w-2xl px-4">
              <div className="flex items-center gap-2 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 focus-within:border-[var(--color-text)]">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={onKeyDown}
                  rows={1}
                  placeholder="Ask Sentinel to investigate or fix an issue…"
                  className="max-h-40 flex-1 resize-none self-center bg-transparent py-1 text-[13.5px] leading-relaxed text-[var(--color-text)] placeholder:text-[var(--color-faint)] focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={busy || input.trim().length === 0}
                  className="shrink-0 rounded bg-[var(--color-text)] border border-[var(--color-text)] px-3 py-1.5 text-xs font-semibold text-[var(--color-bg)] disabled:cursor-not-allowed disabled:bg-transparent disabled:text-[var(--color-faint)] disabled:border-[var(--color-border)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)] transition-all duration-100 flex items-center gap-1"
                >
                  {busy ? "Working" : "Send"}
                  {!busy && (
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  )}
                </button>
              </div>
              <div className="mt-2 px-1 flex items-center justify-between text-[10px] font-mono text-[var(--color-faint)]">
                <span>Enforcing branch namespace checks (sentinel/*) & protected branch blocks.</span>
                <span>gemini-3.5-flash</span>
              </div>
            </form>
          </footer>
        </main>
      </div>
    </div>
  );
}

function applyEvent(
  event: AgentEvent,
  patch: (fn: (t: Extract<Turn, { role: "agent" }>) => void) => void,
) {
  switch (event.type) {
    case "reasoning":
      patch((t) => t.agency.push({ kind: "reasoning", text: event.text }));
      break;
    case "tool_call":
      patch((t) => t.agency.push({ kind: "tool_call", name: event.name, args: event.args }));
      break;
    case "tool_result":
      patch((t) => t.agency.push({ kind: "tool_result", name: event.name }));
      break;
    case "final":
      patch((t) => {
        t.text = event.text;
        if (t.status === "working") t.status = "done";
      });
      break;
    case "aborted":
      patch((t) => {
        t.status = "aborted";
        t.text = event.message;
        t.agency.push({ kind: "status", text: event.message, tone: "danger" });
      });
      break;
    case "error":
      patch((t) => {
        t.status = "error";
        t.text = event.message;
        t.agency.push({ kind: "status", text: event.message, tone: "danger" });
      });
      break;
    case "done":
      patch((t) => {
        if (t.status === "working") t.status = "done";
      });
      break;
  }
}

function Header({ user, onLogout }: { user: GitlabUser; onLogout: () => void }) {
  return (
    <header className="flex shrink-0 items-center justify-between border-b border-[var(--color-border)] px-4 py-3 bg-[var(--color-bg)]">
      <div className="flex items-center gap-2">
        <div className="h-4.5 w-4.5 text-[var(--color-text)]">
          <LogoSVG />
        </div>
        <span className="text-sm font-semibold tracking-tight text-[var(--color-text)]">
          Sentinel
        </span>
        <span className="font-mono text-[9px] text-[var(--color-faint)] border border-[var(--color-border)] rounded px-1.5 py-0.2">
          SRE Overwatch
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-muted)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text)] pulse-indicator"></span>
          <span>Google Cloud: <strong className="text-[var(--color-text)] font-medium">Live</strong></span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[var(--color-muted)]">
          {user.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_url} alt="" className="h-4 w-4 rounded-full" />
          ) : (
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text)]"></span>
          )}
          <span>GitLab: <strong className="text-[var(--color-text)] font-medium">@{user.username}</strong></span>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="rounded border border-[var(--color-border)] px-2 py-1 text-[10px] font-medium text-[var(--color-muted)] hover:border-[var(--color-text)] hover:text-[var(--color-text)] transition-colors"
        >
          Disconnect
        </button>
      </div>
    </header>
  );
}

function LoginGate({ loading }: { loading: boolean }) {
  return (
    <div className="flex h-screen flex-col items-center justify-center bg-[var(--color-bg)] px-4">
      <div className="flex flex-col items-center text-center">
        <div className="relative flex items-center justify-center gap-3 mb-4" style={{ left: "-32px" }}>
          <div className="h-12 w-12 text-[var(--color-text)] shrink-0 flex items-center justify-center">
            <LogoSVG />
          </div>
          <h1
            className="font-sans text-5xl font-semibold tracking-tight leading-none text-[var(--color-text)]"
            style={{ letterSpacing: "-0.035em" }}
          >
            Sentinel
          </h1>
        </div>
        <p className="text-[13.5px] leading-relaxed text-[var(--color-muted)] max-w-[420px] mb-7">
          Connect your GitLab account to let Sentinel investigate and remediate issues on
          your behalf — scoped to your own permissions.
        </p>
        {loading ? (
          <div className="font-mono text-xs text-[var(--color-muted)] flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text)] pulse-indicator"></span>
            Checking session…
          </div>
        ) : (
          <a
            href="/api/auth/login"
            className="rounded bg-[var(--color-text)] px-5 py-2.5 text-xs font-semibold text-[var(--color-bg)] border border-[var(--color-text)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)] transition-colors"
          >
            Connect GitLab
          </a>
        )}
      </div>
    </div>
  );
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (s: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="my-auto flex flex-col items-center text-center py-12">
      {/* Centered logo-name block shifted left by 32px relative to centered byline text */}
      <div className="relative flex items-center justify-center gap-3 mb-4" style={{ left: "-32px" }}>
        <div className="h-12 w-12 text-[var(--color-text)] shrink-0 flex items-center justify-center">
          <LogoSVG />
        </div>
        <h1 className="font-sans text-5xl font-semibold tracking-tight leading-none text-[var(--color-text)]" style={{ letterSpacing: "-0.035em" }}>
          Sentinel
        </h1>
      </div>

      <p className="text-[13.5px] leading-relaxed text-[var(--color-muted)] max-w-[420px] mb-7">
        Autonomous SRE oversight and code remediation agent for GitLab repositories.
      </p>

      <div className="flex w-full flex-col gap-2">
        {SUGGESTIONS.map((s, idx) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            disabled={disabled}
            className="flex items-center justify-between rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-left text-[12.5px] leading-relaxed text-[var(--color-muted)] hover:bg-[var(--color-surface-2)] hover:border-[var(--color-text)] hover:text-[var(--color-text)] disabled:cursor-not-allowed transition-all duration-100 group"
          >
            <span className="flex items-center">
              <span className="font-mono text-[10px] text-[var(--color-faint)] mr-3">0{idx + 1}</span>
              <span className="flex-1 text-[var(--color-text)]">{s}</span>
            </span>
            <span className="text-[var(--color-faint)] group-hover:text-[var(--color-text)] transition-colors text-xs font-semibold">→</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function UserMessage({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-[13.5px] leading-relaxed text-[var(--color-text)]">
        {text}
      </div>
    </div>
  );
}

function AgentMessage({ turn }: { turn: Extract<Turn, { role: "agent" }> }) {
  const showWorking = turn.status === "working" && turn.text.length === 0;
  return (
    <div className="flex flex-col">
      <AgencyLog entries={turn.agency} status={turn.status} />
      {turn.text ? (
        <div className="rounded border border-[var(--color-border)] p-4 bg-transparent">
          <Markdown>{turn.text}</Markdown>
        </div>
      ) : showWorking ? (
        <div className="font-mono text-xs text-[var(--color-muted)] flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text)] pulse-indicator"></span>
          Working…
        </div>
      ) : null}
    </div>
  );
}
