"use client";

import { motion } from "motion/react";

/**
 * Wraps page content with a subtle fade/slide-in so navigating between
 * Timeline, Live, and Settings feels fluid rather than abrupt.
 */
export default function PageTransition({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}